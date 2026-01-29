"use client";

import * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { cva, type VariantProps } from "class-variance-authority";
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// Toast Types
// =============================================================================

type ToastType = "default" | "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  title?: string;
  description?: string;
  type: ToastType;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

type ToastInput = Omit<Toast, "id">;

interface ToastContextValue {
  toasts: Toast[];
  toast: (input: ToastInput) => void;
  dismiss: (id: string) => void;
}

// =============================================================================
// Toast Context
// =============================================================================

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

/**
 * Hook to access toast functionality.
 *
 * @example
 * ```tsx
 * const { toast } = useToast();
 *
 * toast({
 *   title: "Success!",
 *   description: "Lead exported successfully.",
 *   type: "success",
 * });
 * ```
 */
export function useToast(): { toast: (input: ToastInput) => void; dismiss: (id: string) => void } {
  const context = React.useContext(ToastContext);

  if (!context) {
    // Return no-op functions if outside provider (prevents crashes during SSR)
    return {
      toast: (input: ToastInput) => {
        if (typeof window !== "undefined") {
          console.warn("useToast called outside of ToastProvider. Toast not shown:", input);
        }
      },
      dismiss: () => {},
    };
  }

  return { toast: context.toast, dismiss: context.dismiss };
}

// =============================================================================
// Toast Styles
// =============================================================================

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-4 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full",
  {
    variants: {
      variant: {
        default: "border bg-background text-foreground",
        success:
          "border-green-200 bg-green-50 text-green-900 dark:border-green-800 dark:bg-green-900/20 dark:text-green-100",
        error:
          "border-red-200 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-900/20 dark:text-red-100",
        warning:
          "border-yellow-200 bg-yellow-50 text-yellow-900 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-100",
        info: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-100",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

// =============================================================================
// Toast Icon Component
// =============================================================================

function ToastIcon({ type }: { type: ToastType }): JSX.Element {
  const iconMap: Record<ToastType, React.ComponentType<{ className?: string }>> = {
    default: Info,
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const colorMap: Record<ToastType, string> = {
    default: "text-foreground",
    success: "text-green-600 dark:text-green-400",
    error: "text-red-600 dark:text-red-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    info: "text-blue-600 dark:text-blue-400",
  };

  const Icon = iconMap[type];
  return <Icon className={cn("h-5 w-5 flex-shrink-0", colorMap[type])} />;
}

// =============================================================================
// Toast Item Component
// =============================================================================

interface ToastItemProps extends VariantProps<typeof toastVariants> {
  toast: Toast;
  onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps): JSX.Element {
  return (
    <ToastPrimitives.Root
      className={cn(toastVariants({ variant: toast.type }))}
      duration={toast.duration ?? 5000}
      onOpenChange={(open) => {
        if (!open) onDismiss(toast.id);
      }}
    >
      <div className="flex items-start gap-3">
        <ToastIcon type={toast.type} />
        <div className="grid gap-1">
          {toast.title && (
            <ToastPrimitives.Title className="text-sm font-semibold">
              {toast.title}
            </ToastPrimitives.Title>
          )}
          {toast.description && (
            <ToastPrimitives.Description className="text-sm opacity-90">
              {toast.description}
            </ToastPrimitives.Description>
          )}
        </div>
      </div>
      {toast.action && (
        <ToastPrimitives.Action
          altText={toast.action.label}
          onClick={toast.action.onClick}
          className="inline-flex h-8 shrink-0 items-center justify-center rounded-md border bg-transparent px-3 text-sm font-medium transition-colors hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          {toast.action.label}
        </ToastPrimitives.Action>
      )}
      <ToastPrimitives.Close className="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none group-hover:opacity-100">
        <X className="h-4 w-4" />
      </ToastPrimitives.Close>
    </ToastPrimitives.Root>
  );
}

// =============================================================================
// Toast Provider Component
// =============================================================================

interface ToastProviderProps {
  children: React.ReactNode;
}

/**
 * Toast provider component that enables toast notifications.
 *
 * Wrap your application with this provider to enable the useToast hook.
 *
 * @example
 * ```tsx
 * <ToastProvider>
 *   <App />
 *   <ToastViewport />
 * </ToastProvider>
 * ```
 */
export function ToastProvider({ children }: ToastProviderProps): JSX.Element {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const toast = React.useCallback((input: ToastInput) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setToasts((prev) => [...prev, { ...input, id }]);
  }, []);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const contextValue = React.useMemo(
    () => ({ toasts, toast, dismiss }),
    [toasts, toast, dismiss]
  );

  return (
    <ToastContext.Provider value={contextValue}>
      <ToastPrimitives.Provider swipeDirection="right">
        {children}
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </ToastPrimitives.Provider>
    </ToastContext.Provider>
  );
}

// =============================================================================
// Toast Viewport Component
// =============================================================================

/**
 * Toast viewport - renders the toast container.
 * Place this at the end of your ToastProvider children.
 */
export function ToastViewport(): JSX.Element {
  return (
    <ToastPrimitives.Viewport
      className={cn(
        "fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]"
      )}
    />
  );
}
