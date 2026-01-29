"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  /** Size of the spinner */
  size?: "sm" | "md" | "lg";
  /** Additional CSS classes */
  className?: string;
}

/**
 * Loading spinner component.
 *
 * @example
 * ```tsx
 * <LoadingSpinner size="md" />
 * ```
 */
export function LoadingSpinner({
  size = "md",
  className,
}: LoadingSpinnerProps): JSX.Element {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  return (
    <Loader2
      className={cn("animate-spin text-primary", sizeClasses[size], className)}
    />
  );
}

interface LoadingOverlayProps {
  /** Whether the overlay is visible */
  isLoading: boolean;
  /** Loading message to display */
  message?: string;
  /** Additional CSS classes */
  className?: string;
  /** Children to render underneath the overlay */
  children?: React.ReactNode;
}

/**
 * Full-screen loading overlay.
 *
 * @example
 * ```tsx
 * <LoadingOverlay isLoading={isLoading} message="Loading data...">
 *   <MyContent />
 * </LoadingOverlay>
 * ```
 */
export function LoadingOverlay({
  isLoading,
  message,
  className,
  children,
}: LoadingOverlayProps): JSX.Element {
  return (
    <div className={cn("relative", className)}>
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex flex-col items-center justify-center z-50">
          <LoadingSpinner size="lg" />
          {message && (
            <p className="mt-4 text-sm text-muted-foreground">{message}</p>
          )}
        </div>
      )}
    </div>
  );
}

interface LoadingCardProps {
  /** Loading message */
  message?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Loading card placeholder.
 *
 * @example
 * ```tsx
 * {isLoading ? <LoadingCard message="Fetching data..." /> : <MyContent />}
 * ```
 */
export function LoadingCard({
  message = "Loading...",
  className,
}: LoadingCardProps): JSX.Element {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 text-center",
        className
      )}
    >
      <LoadingSpinner size="lg" />
      <p className="mt-4 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

interface LoadingButtonProps {
  /** Whether the button is in loading state */
  isLoading: boolean;
  /** Loading text to display */
  loadingText?: string;
  /** Default text when not loading */
  children: React.ReactNode;
  /** Button click handler */
  onClick?: () => void;
  /** Whether button is disabled */
  disabled?: boolean;
  /** Button variant */
  variant?: "default" | "destructive" | "outline" | "ghost";
  /** Additional CSS classes */
  className?: string;
  /** Button type */
  type?: "button" | "submit" | "reset";
}

/**
 * Button with loading state.
 *
 * @example
 * ```tsx
 * <LoadingButton
 *   isLoading={isPending}
 *   loadingText="Saving..."
 *   onClick={handleSave}
 * >
 *   Save
 * </LoadingButton>
 * ```
 */
export function LoadingButton({
  isLoading,
  loadingText,
  children,
  onClick,
  disabled,
  variant = "default",
  className,
  type = "button",
}: LoadingButtonProps): JSX.Element {
  const variantClasses = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    destructive:
      "bg-destructive text-destructive-foreground hover:bg-destructive/90",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    ghost: "hover:bg-accent hover:text-accent-foreground",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isLoading || disabled}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        className
      )}
    >
      {isLoading && <LoadingSpinner size="sm" />}
      {isLoading && loadingText ? loadingText : children}
    </button>
  );
}
