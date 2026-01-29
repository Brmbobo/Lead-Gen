"use client";

import { AlertCircle, RefreshCw, WifiOff, ServerCrash, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { isApiError, ErrorCode, type ErrorCodeType } from "@/lib/api";

interface ErrorCardProps {
  /** Error object or message */
  error: Error | string;
  /** Retry callback */
  onRetry?: () => void;
  /** Whether retry is in progress */
  isRetrying?: boolean;
  /** Custom title */
  title?: string;
  /** Additional CSS classes */
  className?: string;
  /** Variant style */
  variant?: "default" | "inline" | "minimal";
}

/**
 * Error display component with retry functionality.
 *
 * Automatically detects API error types and displays appropriate icons and messages.
 *
 * @example
 * ```tsx
 * <ErrorCard
 *   error={error}
 *   onRetry={() => refetch()}
 *   isRetrying={isFetching}
 * />
 * ```
 */
export function ErrorCard({
  error,
  onRetry,
  isRetrying = false,
  title,
  className,
  variant = "default",
}: ErrorCardProps): JSX.Element {
  const errorMessage = typeof error === "string" ? error : error.message;
  const errorCode: ErrorCodeType | null = isApiError(error) ? error.code : null;

  // Determine icon based on error type
  const Icon = getErrorIcon(errorCode);

  // Determine title based on error type
  const errorTitle = title || getErrorTitle(errorCode);

  // Check if error is retryable
  const canRetry = onRetry && (isApiError(error) ? error.retryable : true);

  if (variant === "minimal") {
    return (
      <div className={cn("flex items-center gap-2 text-destructive", className)}>
        <Icon className="h-4 w-4" />
        <span className="text-sm">{errorMessage}</span>
        {canRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="text-sm underline hover:no-underline disabled:opacity-50"
          >
            {isRetrying ? "Retrying..." : "Retry"}
          </button>
        )}
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 p-3 rounded-md bg-destructive/10 text-destructive",
          className
        )}
      >
        <Icon className="h-5 w-5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{errorTitle}</p>
          <p className="text-sm opacity-90 truncate">{errorMessage}</p>
        </div>
        {canRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="flex items-center gap-1 px-3 py-1 text-sm font-medium rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
          >
            <RefreshCw
              className={cn("h-3 w-3", isRetrying && "animate-spin")}
            />
            {isRetrying ? "Retrying" : "Retry"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-destructive/20 bg-destructive/5 p-6",
        className
      )}
    >
      <div className="flex flex-col items-center text-center">
        <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
          <Icon className="h-6 w-6 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold text-destructive mb-2">
          {errorTitle}
        </h3>
        <p className="text-sm text-muted-foreground mb-4 max-w-md">
          {errorMessage}
        </p>
        {canRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-destructive text-destructive-foreground text-sm font-medium hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw
              className={cn("h-4 w-4", isRetrying && "animate-spin")}
            />
            {isRetrying ? "Retrying..." : "Try Again"}
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Get appropriate icon for error type.
 */
function getErrorIcon(
  errorCode: ErrorCodeType | null
): React.ComponentType<{ className?: string }> {
  if (!errorCode) return AlertCircle;

  switch (errorCode) {
    case ErrorCode.NETWORK_ERROR:
      return WifiOff;
    case ErrorCode.UNAUTHORIZED:
    case ErrorCode.FORBIDDEN:
      return Lock;
    case ErrorCode.SERVICE_UNAVAILABLE:
    case ErrorCode.INTERNAL_ERROR:
    case ErrorCode.GATEWAY_TIMEOUT:
      return ServerCrash;
    default:
      return AlertCircle;
  }
}

/**
 * Get appropriate title for error type.
 */
function getErrorTitle(errorCode: ErrorCodeType | null): string {
  if (!errorCode) return "Something went wrong";

  switch (errorCode) {
    case ErrorCode.NETWORK_ERROR:
      return "Connection Error";
    case ErrorCode.UNAUTHORIZED:
      return "Authentication Required";
    case ErrorCode.FORBIDDEN:
      return "Access Denied";
    case ErrorCode.NOT_FOUND:
      return "Not Found";
    case ErrorCode.RATE_LIMITED:
      return "Rate Limited";
    case ErrorCode.SERVICE_UNAVAILABLE:
      return "Service Unavailable";
    case ErrorCode.TIMEOUT:
    case ErrorCode.GATEWAY_TIMEOUT:
      return "Request Timeout";
    case ErrorCode.VALIDATION_ERROR:
      return "Validation Error";
    default:
      return "Something went wrong";
  }
}

/**
 * Inline error message for form fields.
 */
export function ErrorMessage({
  message,
  className,
}: {
  message: string;
  className?: string;
}): JSX.Element {
  return (
    <p className={cn("text-sm text-destructive mt-1", className)}>
      {message}
    </p>
  );
}
