"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { WorkflowCard, WorkflowCardSkeleton } from "./workflow-card";
import { ErrorCard } from "@/components/ui/error-card";
import { EmptyWorkflows } from "@/components/ui/empty-state";
import { useWorkflows, useRunWorkflow, useStopWorkflow } from "@/hooks";
import { useToast } from "@/components/ui/toast-provider";

interface WorkflowsGridProps {
  /** Maximum number of workflows to display */
  maxItems?: number;
  /** Callback when create workflow is clicked */
  onCreateWorkflow?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Workflows grid component displaying workflow cards.
 *
 * Fetches workflows and provides run/stop functionality.
 *
 * @example
 * ```tsx
 * <WorkflowsGrid
 *   maxItems={4}
 *   onCreateWorkflow={() => router.push('/workflows/new')}
 * />
 * ```
 */
export function WorkflowsGrid({
  maxItems = 4,
  onCreateWorkflow,
  className,
}: WorkflowsGridProps): JSX.Element {
  const { workflows, isLoading, isError, error, refetch, isFetching } = useWorkflows();
  const { toast } = useToast();

  const { runWorkflow, isRunning: isRunningWorkflow } = useRunWorkflow({
    onSuccess: () => {
      toast({
        title: "Workflow started",
        description: "The workflow is now running.",
        type: "success",
      });
    },
    onError: (err) => {
      toast({
        title: "Failed to start workflow",
        description: err.message,
        type: "error",
      });
    },
  });

  const { stopWorkflow, isStopping: isStoppingWorkflow } = useStopWorkflow({
    onSuccess: () => {
      toast({
        title: "Workflow stopped",
        description: "The workflow has been stopped.",
        type: "info",
      });
    },
    onError: (err) => {
      toast({
        title: "Failed to stop workflow",
        description: err.message,
        type: "error",
      });
    },
  });

  // Track which workflow action is in progress
  const [activeWorkflowId, setActiveWorkflowId] = React.useState<string | null>(null);

  const handleRun = async (workflowId: string): Promise<void> => {
    setActiveWorkflowId(workflowId);
    try {
      await runWorkflow(workflowId);
    } finally {
      setActiveWorkflowId(null);
    }
  };

  const handleStop = async (workflowId: string): Promise<void> => {
    setActiveWorkflowId(workflowId);
    try {
      await stopWorkflow(workflowId);
    } finally {
      setActiveWorkflowId(null);
    }
  };

  // Limit workflows displayed
  const displayedWorkflows = workflows.slice(0, maxItems);

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Active Workflows</h3>
        {workflows.length > maxItems && (
          <span className="text-sm text-muted-foreground">
            Showing {maxItems} of {workflows.length}
          </span>
        )}
      </div>

      {isError && error ? (
        <ErrorCard
          error={error}
          onRetry={() => refetch()}
          isRetrying={isFetching}
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: maxItems }).map((_, i) => (
            <WorkflowCardSkeleton key={i} />
          ))}
        </div>
      ) : displayedWorkflows.length === 0 ? (
        <EmptyWorkflows onAction={onCreateWorkflow} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayedWorkflows.map((workflow) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              onRun={() => handleRun(workflow.id)}
              onStop={() => handleStop(workflow.id)}
              isRunning={activeWorkflowId === workflow.id && isRunningWorkflow}
              isStopping={activeWorkflowId === workflow.id && isStoppingWorkflow}
            />
          ))}
        </div>
      )}
    </div>
  );
}
