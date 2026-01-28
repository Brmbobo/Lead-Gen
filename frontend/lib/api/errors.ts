/**
 * API error handling utilities.
 *
 * Provides typed error classes and transformation functions
 * for handling API errors consistently across the application.
 */

import type { ApiErrorResponse } from './types';

// =============================================================================
// Error Codes
// =============================================================================

/** Standard API error codes */
export const ErrorCode = {
  // Client errors (4xx)
  BAD_REQUEST: 'BAD_REQUEST',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  RATE_LIMITED: 'RATE_LIMITED',
  PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',

  // Server errors (5xx)
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  GATEWAY_TIMEOUT: 'GATEWAY_TIMEOUT',

  // Custom application errors
  WORKFLOW_RUNNING: 'WORKFLOW_RUNNING',
  WORKFLOW_NOT_FOUND: 'WORKFLOW_NOT_FOUND',
  LEAD_NOT_FOUND: 'LEAD_NOT_FOUND',
  EXPORT_FAILED: 'EXPORT_FAILED',
  ENRICHMENT_FAILED: 'ENRICHMENT_FAILED',
  API_KEY_INVALID: 'API_KEY_INVALID',
  API_KEY_EXPIRED: 'API_KEY_EXPIRED',
  QUOTA_EXCEEDED: 'QUOTA_EXCEEDED',

  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  ABORTED: 'ABORTED',

  // Unknown
  UNKNOWN: 'UNKNOWN',
} as const;

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode];

// =============================================================================
// API Error Class
// =============================================================================

/**
 * Custom error class for API errors.
 *
 * Provides structured error information with type safety.
 */
export class ApiError extends Error {
  /** Error code for programmatic handling */
  public readonly code: ErrorCodeType;

  /** HTTP status code (if applicable) */
  public readonly status: number | null;

  /** Additional error details */
  public readonly details: Record<string, unknown> | null;

  /** Request correlation ID for debugging */
  public readonly correlationId: string | null;

  /** Timestamp when error occurred */
  public readonly timestamp: Date;

  /** Whether this error is retryable */
  public readonly retryable: boolean;

  constructor(
    message: string,
    code: ErrorCodeType = ErrorCode.UNKNOWN,
    options: {
      status?: number;
      details?: Record<string, unknown>;
      correlationId?: string;
      cause?: Error;
    } = {}
  ) {
    super(message, { cause: options.cause });

    this.name = 'ApiError';
    this.code = code;
    this.status = options.status ?? null;
    this.details = options.details ?? null;
    this.correlationId = options.correlationId ?? null;
    this.timestamp = new Date();
    this.retryable = this.isRetryable();

    // Maintains proper stack trace for where error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }

  /**
   * Determines if this error type is retryable.
   */
  private isRetryable(): boolean {
    const retryableCodes: ErrorCodeType[] = [
      ErrorCode.RATE_LIMITED,
      ErrorCode.SERVICE_UNAVAILABLE,
      ErrorCode.GATEWAY_TIMEOUT,
      ErrorCode.NETWORK_ERROR,
      ErrorCode.TIMEOUT,
    ];

    return retryableCodes.includes(this.code);
  }

  /**
   * Returns a user-friendly error message.
   */
  public getUserMessage(): string {
    const messages: Record<ErrorCodeType, string> = {
      [ErrorCode.BAD_REQUEST]: 'Invalid request. Please check your input.',
      [ErrorCode.UNAUTHORIZED]: 'Please log in to continue.',
      [ErrorCode.FORBIDDEN]: 'You do not have permission to perform this action.',
      [ErrorCode.NOT_FOUND]: 'The requested resource was not found.',
      [ErrorCode.CONFLICT]: 'A conflict occurred. Please refresh and try again.',
      [ErrorCode.VALIDATION_ERROR]: 'Please check your input and try again.',
      [ErrorCode.RATE_LIMITED]: 'Too many requests. Please wait a moment.',
      [ErrorCode.PAYLOAD_TOO_LARGE]: 'The request is too large.',
      [ErrorCode.INTERNAL_ERROR]: 'An unexpected error occurred. Please try again.',
      [ErrorCode.SERVICE_UNAVAILABLE]: 'Service temporarily unavailable. Please try again later.',
      [ErrorCode.GATEWAY_TIMEOUT]: 'Request timed out. Please try again.',
      [ErrorCode.WORKFLOW_RUNNING]: 'This workflow is already running.',
      [ErrorCode.WORKFLOW_NOT_FOUND]: 'Workflow not found.',
      [ErrorCode.LEAD_NOT_FOUND]: 'Lead not found.',
      [ErrorCode.EXPORT_FAILED]: 'Export failed. Please try again.',
      [ErrorCode.ENRICHMENT_FAILED]: 'Email enrichment failed. Please check your API key.',
      [ErrorCode.API_KEY_INVALID]: 'Invalid API key. Please check your settings.',
      [ErrorCode.API_KEY_EXPIRED]: 'API key has expired. Please update your settings.',
      [ErrorCode.QUOTA_EXCEEDED]: 'API quota exceeded. Please upgrade your plan.',
      [ErrorCode.NETWORK_ERROR]: 'Network error. Please check your connection.',
      [ErrorCode.TIMEOUT]: 'Request timed out. Please try again.',
      [ErrorCode.ABORTED]: 'Request was cancelled.',
      [ErrorCode.UNKNOWN]: 'An unexpected error occurred.',
    };

    return messages[this.code] || this.message;
  }

  /**
   * Converts error to JSON-serializable object.
   */
  public toJSON(): ApiErrorResponse {
    return {
      code: this.code,
      message: this.message,
      details: this.details ?? undefined,
      correlation_id: this.correlationId ?? undefined,
      timestamp: this.timestamp.toISOString(),
    };
  }

  /**
   * Creates ApiError from HTTP response.
   */
  public static async fromResponse(response: Response, correlationId?: string): Promise<ApiError> {
    const status = response.status;
    let code = ErrorCode.UNKNOWN;
    let message = 'An error occurred';
    let details: Record<string, unknown> | undefined;

    // Map HTTP status to error code
    const statusCodeMap: Record<number, ErrorCodeType> = {
      400: ErrorCode.BAD_REQUEST,
      401: ErrorCode.UNAUTHORIZED,
      403: ErrorCode.FORBIDDEN,
      404: ErrorCode.NOT_FOUND,
      409: ErrorCode.CONFLICT,
      422: ErrorCode.VALIDATION_ERROR,
      429: ErrorCode.RATE_LIMITED,
      413: ErrorCode.PAYLOAD_TOO_LARGE,
      500: ErrorCode.INTERNAL_ERROR,
      502: ErrorCode.SERVICE_UNAVAILABLE,
      503: ErrorCode.SERVICE_UNAVAILABLE,
      504: ErrorCode.GATEWAY_TIMEOUT,
    };

    code = statusCodeMap[status] || ErrorCode.UNKNOWN;

    // Try to parse error body
    try {
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const body = await response.json();

        if (body.code) {
          code = body.code as ErrorCodeType;
        }
        if (body.message) {
          message = body.message;
        }
        if (body.details) {
          details = body.details;
        }
        if (body.correlation_id && !correlationId) {
          correlationId = body.correlation_id;
        }
      } else {
        message = await response.text();
      }
    } catch {
      message = response.statusText || 'Request failed';
    }

    return new ApiError(message, code, {
      status,
      details,
      correlationId,
    });
  }

  /**
   * Creates ApiError from fetch error (network issues, etc.)
   */
  public static fromFetchError(error: Error, correlationId?: string): ApiError {
    // Handle abort errors
    if (error.name === 'AbortError') {
      return new ApiError('Request was aborted', ErrorCode.ABORTED, {
        correlationId,
        cause: error,
      });
    }

    // Handle timeout errors
    if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
      return new ApiError('Request timed out', ErrorCode.TIMEOUT, {
        correlationId,
        cause: error,
      });
    }

    // Handle network errors
    if (error.message.includes('network') || error.message.includes('fetch')) {
      return new ApiError('Network error occurred', ErrorCode.NETWORK_ERROR, {
        correlationId,
        cause: error,
      });
    }

    // Generic error
    return new ApiError(error.message || 'An error occurred', ErrorCode.UNKNOWN, {
      correlationId,
      cause: error,
    });
  }
}

// =============================================================================
// Error Type Guards
// =============================================================================

/**
 * Type guard to check if an error is an ApiError.
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/**
 * Type guard to check if error is a specific type.
 */
export function isErrorCode(error: unknown, code: ErrorCodeType): boolean {
  return isApiError(error) && error.code === code;
}

/**
 * Type guard for network errors.
 */
export function isNetworkError(error: unknown): boolean {
  return isApiError(error) && error.code === ErrorCode.NETWORK_ERROR;
}

/**
 * Type guard for authentication errors.
 */
export function isAuthError(error: unknown): boolean {
  return (
    isApiError(error) &&
    (error.code === ErrorCode.UNAUTHORIZED || error.code === ErrorCode.FORBIDDEN)
  );
}

/**
 * Type guard for retryable errors.
 */
export function isRetryableError(error: unknown): boolean {
  return isApiError(error) && error.retryable;
}

// =============================================================================
// Error Handling Utilities
// =============================================================================

/**
 * Wraps an async function with error transformation.
 */
export async function withErrorHandling<T>(
  fn: () => Promise<T>,
  correlationId?: string
): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (isApiError(error)) {
      throw error;
    }
    if (error instanceof Error) {
      throw ApiError.fromFetchError(error, correlationId);
    }
    throw new ApiError('An unexpected error occurred', ErrorCode.UNKNOWN, {
      correlationId,
    });
  }
}

/**
 * Extracts user-friendly message from any error.
 */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.getUserMessage();
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

/**
 * Creates a validation error from field errors.
 */
export function createValidationError(
  fieldErrors: Record<string, string[]>,
  correlationId?: string
): ApiError {
  const messages = Object.entries(fieldErrors)
    .flatMap(([field, errors]) => errors.map((e) => `${field}: ${e}`))
    .join('; ');

  return new ApiError(messages || 'Validation failed', ErrorCode.VALIDATION_ERROR, {
    status: 422,
    details: { field_errors: fieldErrors },
    correlationId,
  });
}
