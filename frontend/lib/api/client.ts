/**
 * Base API client for the Lead-Gen application.
 *
 * Provides a type-safe fetch wrapper with:
 * - Automatic JSON handling
 * - Error transformation
 * - Request/response interceptors
 * - Correlation ID injection
 * - Optional auth header support
 * - Configurable timeout
 */

import { ApiError, ErrorCode } from './errors';

// =============================================================================
// Configuration
// =============================================================================

/** API client configuration options */
export interface ApiClientConfig {
  /** Base URL for API requests */
  baseUrl: string;

  /** Default request timeout in milliseconds */
  timeout?: number;

  /** Default headers to include in all requests */
  defaultHeaders?: Record<string, string>;

  /** Function to get auth token */
  getAuthToken?: () => string | null | Promise<string | null>;

  /** Called before each request */
  onRequest?: (request: RequestConfig) => RequestConfig | Promise<RequestConfig>;

  /** Called after each response */
  onResponse?: <T>(response: T) => T | Promise<T>;

  /** Called on error */
  onError?: (error: ApiError) => void | Promise<void>;

  /** Enable request/response logging */
  debug?: boolean;
}

/** Request configuration */
export interface RequestConfig extends RequestInit {
  url: string;
  params?: Record<string, string | number | boolean | undefined | null | string[]>;
  timeout?: number;
  correlationId?: string;
}

/** Default configuration values */
const DEFAULT_CONFIG: Partial<ApiClientConfig> = {
  timeout: 30000,
  defaultHeaders: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  debug: false,
};

// =============================================================================
// API Client Class
// =============================================================================

/**
 * Type-safe API client with interceptors and error handling.
 *
 * @example
 * ```ts
 * const client = new ApiClient({
 *   baseUrl: 'http://localhost:8000/api/v1',
 * });
 *
 * const leads = await client.get<Lead[]>('/leads');
 * ```
 */
export class ApiClient {
  private config: Required<
    Pick<ApiClientConfig, 'baseUrl' | 'timeout' | 'defaultHeaders' | 'debug'>
  > &
    Omit<ApiClientConfig, 'baseUrl' | 'timeout' | 'defaultHeaders' | 'debug'>;

  constructor(config: ApiClientConfig) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      defaultHeaders: {
        ...DEFAULT_CONFIG.defaultHeaders,
        ...config.defaultHeaders,
      },
    } as Required<Pick<ApiClientConfig, 'baseUrl' | 'timeout' | 'defaultHeaders' | 'debug'>> &
      Omit<ApiClientConfig, 'baseUrl' | 'timeout' | 'defaultHeaders' | 'debug'>;
  }

  /**
   * Generate a unique correlation ID for request tracing.
   */
  private generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  /**
   * Build URL with query parameters.
   */
  private buildUrl(path: string, params?: RequestConfig['params']): string {
    const url = new URL(path, this.config.baseUrl);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach((v) => url.searchParams.append(key, String(v)));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }

    return url.toString();
  }

  /**
   * Build request headers with auth and correlation ID.
   */
  private async buildHeaders(correlationId: string): Promise<Headers> {
    const headers = new Headers(this.config.defaultHeaders);
    headers.set('X-Correlation-ID', correlationId);

    if (this.config.getAuthToken) {
      const token = await this.config.getAuthToken();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    }

    return headers;
  }

  /**
   * Log request details in debug mode.
   */
  private logRequest(method: string, url: string, correlationId: string): void {
    if (this.config.debug) {
      console.log(`[API] ${method} ${url} (${correlationId})`);
    }
  }

  /**
   * Log response details in debug mode.
   */
  private logResponse(
    method: string,
    url: string,
    status: number,
    correlationId: string,
    duration: number
  ): void {
    if (this.config.debug) {
      console.log(`[API] ${method} ${url} - ${status} (${duration}ms) [${correlationId}]`);
    }
  }

  /**
   * Execute a fetch request with timeout and error handling.
   */
  private async execute<T>(config: RequestConfig): Promise<T> {
    const correlationId = config.correlationId || this.generateCorrelationId();
    const timeout = config.timeout ?? this.config.timeout;

    // Apply request interceptor
    let requestConfig = config;
    if (this.config.onRequest) {
      requestConfig = await this.config.onRequest(config);
    }

    const url = this.buildUrl(requestConfig.url, requestConfig.params);
    const headers = await this.buildHeaders(correlationId);

    // Merge custom headers
    if (requestConfig.headers) {
      const customHeaders = new Headers(requestConfig.headers);
      customHeaders.forEach((value, key) => headers.set(key, value));
    }

    const method = requestConfig.method || 'GET';
    this.logRequest(method, url, correlationId);

    const startTime = Date.now();

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...requestConfig,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const duration = Date.now() - startTime;
      this.logResponse(method, url, response.status, correlationId, duration);

      // Handle error responses
      if (!response.ok) {
        const error = await ApiError.fromResponse(response, correlationId);
        if (this.config.onError) {
          await this.config.onError(error);
        }
        throw error;
      }

      // Parse response
      let data: T;
      const contentType = response.headers.get('content-type');

      if (response.status === 204 || !contentType) {
        data = undefined as T;
      } else if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = (await response.text()) as T;
      }

      // Apply response interceptor
      if (this.config.onResponse) {
        data = await this.config.onResponse(data);
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);

      // Already an ApiError
      if (error instanceof ApiError) {
        throw error;
      }

      // Transform fetch errors
      const apiError = ApiError.fromFetchError(error as Error, correlationId);
      if (this.config.onError) {
        await this.config.onError(apiError);
      }
      throw apiError;
    }
  }

  /**
   * Perform a GET request.
   *
   * @param path - API endpoint path
   * @param params - Query parameters
   * @param options - Additional request options
   */
  public async get<T>(
    path: string,
    params?: RequestConfig['params'],
    options?: Omit<RequestConfig, 'url' | 'method' | 'params' | 'body'>
  ): Promise<T> {
    return this.execute<T>({
      ...options,
      url: path,
      method: 'GET',
      params,
    });
  }

  /**
   * Perform a POST request.
   *
   * @param path - API endpoint path
   * @param body - Request body
   * @param options - Additional request options
   */
  public async post<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestConfig, 'url' | 'method' | 'body'>
  ): Promise<T> {
    return this.execute<T>({
      ...options,
      url: path,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * Perform a PUT request.
   *
   * @param path - API endpoint path
   * @param body - Request body
   * @param options - Additional request options
   */
  public async put<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestConfig, 'url' | 'method' | 'body'>
  ): Promise<T> {
    return this.execute<T>({
      ...options,
      url: path,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * Perform a PATCH request.
   *
   * @param path - API endpoint path
   * @param body - Request body
   * @param options - Additional request options
   */
  public async patch<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestConfig, 'url' | 'method' | 'body'>
  ): Promise<T> {
    return this.execute<T>({
      ...options,
      url: path,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * Perform a DELETE request.
   *
   * @param path - API endpoint path
   * @param options - Additional request options
   */
  public async delete<T>(
    path: string,
    options?: Omit<RequestConfig, 'url' | 'method'>
  ): Promise<T> {
    return this.execute<T>({
      ...options,
      url: path,
      method: 'DELETE',
    });
  }

  /**
   * Upload a file using multipart form data.
   *
   * @param path - API endpoint path
   * @param file - File to upload
   * @param fieldName - Form field name for the file
   * @param additionalData - Additional form data
   */
  public async uploadFile<T>(
    path: string,
    file: File,
    fieldName: string = 'file',
    additionalData?: Record<string, string>
  ): Promise<T> {
    const formData = new FormData();
    formData.append(fieldName, file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const correlationId = this.generateCorrelationId();
    const headers = await this.buildHeaders(correlationId);
    headers.delete('Content-Type'); // Let browser set multipart boundary

    return this.execute<T>({
      url: path,
      method: 'POST',
      body: formData as unknown as BodyInit,
      headers: Object.fromEntries(headers.entries()),
      correlationId,
    });
  }
}

// =============================================================================
// Client Instance
// =============================================================================

/**
 * Get the API base URL from environment.
 */
function getApiBaseUrl(): string {
  // Check for environment variable
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // Default for development
  return 'http://localhost:8000/api/v1';
}

/**
 * Pre-configured API client instance.
 *
 * Use this for all API requests throughout the application.
 */
export const apiClient = new ApiClient({
  baseUrl: getApiBaseUrl(),
  timeout: 30000,
  debug: process.env.NODE_ENV === 'development',
  onError: (error) => {
    // Log errors in development
    if (process.env.NODE_ENV === 'development') {
      console.error('[API Error]', {
        code: error.code,
        message: error.message,
        correlationId: error.correlationId,
        details: error.details,
      });
    }
  },
});

// =============================================================================
// Re-exports
// =============================================================================

export type { ApiClientConfig, RequestConfig };
