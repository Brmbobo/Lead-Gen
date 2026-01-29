"use client";

import { Clock, Play, Square, Loader2 } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import type { Workflow, WorkflowStatus } from "@/lib/api";

export interface WorkflowCardProps {
  /** Workflow data */
  workflow: Workflow;
  /** Callback when run button is clicked */
  onRun?: () => void;
  /** Callback when stop button is clicked */
  onStop?: () => void;
  /** Whether a run operation is in progress */
  isRunning?: boolean;
  /** Whether a stop operation is in progress */
  isStopping?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Workflow card component displaying workflow info and actions.
 *
 * @example
 * ```tsx
 * <WorkflowCard
 *   workflow={workflow}
 *   onRun={() => runWorkflow(workflow.id)}
 *   onStop={() => stopWorkflow(workflow.id)}
 *   isRunning={isRunning}
 * />
 * ```
 */
export function WorkflowCard({
  workflow,
  onRun,
  onStop,
  isRunning = false,
  isStopping = false,
  className,
}: WorkflowCardProps): JSX.Element {
  const isWorkflowRunning = workflow.status === "running";
  const canRun = !isWorkflowRunning && workflow.enabled;
  const canStop = isWorkflowRunning;

  // Determine last run time display
  const lastRunDisplay = workflow.completed_at
    ? formatRelativeTime(workflow.completed_at)
    : workflow.started_at
    ? "Running..."
    : "Never";

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-6 shadow-sm transition-shadow hover:shadow-md",
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold truncate pr-2">{workflow.name}</h4>
        <WorkflowStatusBadge status={workflow.status} />
      </div>

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {workflow.description || "No description"}
      </p>

      {/* Progress bar for running workflows */}
      {isWorkflowRunning && workflow.progress_percent > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>Progress</span>
            <span>{workflow.progress_percent}%</span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${workflow.progress_percent}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {lastRunDisplay}
        </span>

        <div className="flex items-center gap-2">
          {canStop && onStop && (
            <button
              onClick={onStop}
              disabled={isStopping}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-destructive text-destructive-foreground text-sm font-medium hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isStopping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              {isStopping ? "Stopping" : "Stop"}
            </button>
          )}

          {canRun && onRun && (
            <button
              onClick={onRun}
              disabled={isRunning || !workflow.enabled}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {isRunning ? "Starting" : "Run"}
            </button>
          )}

          {!workflow.enabled && !isWorkflowRunning && (
            <span className="text-xs text-muted-foreground px-2 py-1">
              Disabled
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Workflow status badge component.
 */
export function WorkflowStatusBadge({
  status,
}: {
  status: WorkflowStatus;
}): JSX.Element {
  const statusConfig: Record<
    WorkflowStatus,
    { label: string; className: string }
  > = {
    pending: {
      label: "Pending",
      className: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    },
    running: {
      label: "Running",
      className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    paused: {
      label: "Paused",
      className: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    },
    completed: {
      label: "Ready",
      className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    failed: {
      label: "Error",
      className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
    cancelled: {
      label: "Cancelled",
      className: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    },
  };

  const config = statusConfig[status];

  return (
    <span
      className={cn(
        "px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap",
        config.className
      )}
    >
      {status === "running" && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse mr-1.5" />
      )}
      {config.label}
    </span>
  );
}

/**
 * Skeleton loading state for WorkflowCard.
 */
export function WorkflowCardSkeleton({
  className,
}: {
  className?: string;
}): JSX.Element {
  return (
    <div className={cn("rounded-lg border bg-card p-6 shadow-sm", className)}>
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-3/4 mb-4" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-16 rounded-md" />
      </div>
    </div>
  );
}
