/**
 * UI Components Module
 *
 * Re-exports all UI primitives for easier importing.
 *
 * @example
 * ```tsx
 * import {
 *   Skeleton,
 *   ErrorCard,
 *   EmptyState,
 *   LoadingSpinner,
 * } from '@/components/ui';
 * ```
 */

// Skeleton components
export {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonWorkflowCard,
  SkeletonActivityItem,
} from "./skeleton";

// Error handling
export { ErrorCard, ErrorMessage } from "./error-card";
export { ErrorBoundary, ErrorFallback, withErrorBoundary } from "./error-boundary";

// Empty states
export {
  EmptyState,
  EmptyLeads,
  EmptyWorkflows,
  EmptySearchResults,
  EmptyActivity,
} from "./empty-state";

// Loading components
export {
  LoadingSpinner,
  LoadingOverlay,
  LoadingCard,
  LoadingButton,
} from "./loading";

// Toast notifications
export { ToastProvider, ToastViewport, useToast } from "./toast-provider";
export {
  Toaster,
  useToast as useToasterToast,
  toast,
  setGlobalToast,
} from "./toaster";
