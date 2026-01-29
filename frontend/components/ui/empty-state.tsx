import { cn } from "@/lib/utils";
import {
  Inbox,
  Search,
  FileQuestion,
  Workflow,
  Users,
  type LucideIcon,
} from "lucide-react";

interface EmptyStateProps {
  /** Title text */
  title: string;
  /** Description text */
  description?: string;
  /** Custom icon component */
  icon?: LucideIcon;
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Additional CSS classes */
  className?: string;
  /** Variant size */
  variant?: "default" | "compact";
}

/**
 * Empty state component for when there's no data to display.
 *
 * @example
 * ```tsx
 * <EmptyState
 *   title="No leads found"
 *   description="Get started by running a workflow to scrape leads."
 *   icon={Users}
 *   action={{
 *     label: "Create Workflow",
 *     onClick: () => router.push("/workflows/new")
 *   }}
 * />
 * ```
 */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className,
  variant = "default",
}: EmptyStateProps): JSX.Element {
  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-8 text-center",
          className
        )}
      >
        <Icon className="h-8 w-8 text-muted-foreground/50 mb-2" />
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground/70 mt-1">{description}</p>
        )}
        {action && (
          <button
            onClick={action.onClick}
            className="mt-3 text-sm text-primary hover:underline"
          >
            {action.label}
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 text-center",
        className
      )}
    >
      <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground max-w-sm mb-6">
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

/**
 * Pre-configured empty state for leads.
 */
export function EmptyLeads({
  onAction,
  className,
}: {
  onAction?: () => void;
  className?: string;
}): JSX.Element {
  return (
    <EmptyState
      title="No leads yet"
      description="Start by running a workflow to scrape leads from Google Places or other sources."
      icon={Users}
      action={
        onAction
          ? {
              label: "Run Workflow",
              onClick: onAction,
            }
          : undefined
      }
      className={className}
    />
  );
}

/**
 * Pre-configured empty state for workflows.
 */
export function EmptyWorkflows({
  onAction,
  className,
}: {
  onAction?: () => void;
  className?: string;
}): JSX.Element {
  return (
    <EmptyState
      title="No workflows"
      description="Create your first workflow to start generating leads automatically."
      icon={Workflow}
      action={
        onAction
          ? {
              label: "Create Workflow",
              onClick: onAction,
            }
          : undefined
      }
      className={className}
    />
  );
}

/**
 * Pre-configured empty state for search results.
 */
export function EmptySearchResults({
  query,
  className,
}: {
  query?: string;
  className?: string;
}): JSX.Element {
  return (
    <EmptyState
      title="No results found"
      description={
        query
          ? `No results found for "${query}". Try adjusting your search.`
          : "No results match your search criteria."
      }
      icon={Search}
      className={className}
    />
  );
}

/**
 * Pre-configured empty state for activities.
 */
export function EmptyActivity({
  className,
}: {
  className?: string;
}): JSX.Element {
  return (
    <EmptyState
      title="No recent activity"
      description="Activity will appear here once you start running workflows."
      icon={FileQuestion}
      variant="compact"
      className={className}
    />
  );
}
