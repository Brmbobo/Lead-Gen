"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDashboardStats,
  getWorkflows,
  runWorkflow,
  stopWorkflow,
  type DashboardStats,
  type Workflow,
  type PaginatedResponse,
} from "@/lib/api";

// =============================================================================
// Query Keys
// =============================================================================

export const dashboardKeys = {
  all: ["dashboard"] as const,
  stats: () => [...dashboardKeys.all, "stats"] as const,
};

export const workflowKeys = {
  all: ["workflows"] as const,
  lists: () => [...workflowKeys.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...workflowKeys.lists(), filters] as const,
  details: () => [...workflowKeys.all, "detail"] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
};

// =============================================================================
// Dashboard Stats Hook
// =============================================================================

interface UseDashboardStatsResult {
  data: DashboardStats | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
  isFetching: boolean;
}

/**
 * Hook to fetch dashboard statistics.
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useDashboardStats();
 *
 * if (isLoading) return <Skeleton />;
 * if (error) return <ErrorCard error={error} />;
 *
 * return <StatsGrid stats={data} />;
 * ```
 */
export function useDashboardStats(): UseDashboardStatsResult {
  const query = useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: getDashboardStats,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isFetching: query.isFetching,
  };
}

// =============================================================================
// Workflows Hook
// =============================================================================

interface UseWorkflowsOptions {
  enabled?: boolean;
  page?: number;
  pageSize?: number;
}

interface UseWorkflowsResult {
  data: PaginatedResponse<Workflow> | undefined;
  workflows: Workflow[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
  isFetching: boolean;
}

/**
 * Hook to fetch workflows list.
 *
 * @example
 * ```tsx
 * const { workflows, isLoading, error } = useWorkflows();
 *
 * if (isLoading) return <SkeletonWorkflowCard />;
 * if (error) return <ErrorCard error={error} />;
 *
 * return workflows.map(w => <WorkflowCard key={w.id} workflow={w} />);
 * ```
 */
export function useWorkflows(options: UseWorkflowsOptions = {}): UseWorkflowsResult {
  const { enabled = true, page = 1, pageSize = 10 } = options;

  const query = useQuery({
    queryKey: workflowKeys.list({ page, pageSize }),
    queryFn: () => getWorkflows({ page, page_size: pageSize }),
    enabled,
    staleTime: 30 * 1000,
  });

  return {
    data: query.data,
    workflows: query.data?.items ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isFetching: query.isFetching,
  };
}

// =============================================================================
// Run Workflow Mutation
// =============================================================================

interface UseRunWorkflowResult {
  runWorkflow: (id: string) => Promise<void>;
  isRunning: boolean;
  error: Error | null;
}

/**
 * Hook to run a workflow.
 *
 * @example
 * ```tsx
 * const { runWorkflow, isRunning } = useRunWorkflow({
 *   onSuccess: () => toast({ title: "Workflow started!" }),
 *   onError: (err) => toast({ title: "Failed", type: "error" }),
 * });
 *
 * <Button onClick={() => runWorkflow(id)} disabled={isRunning}>
 *   {isRunning ? "Starting..." : "Run"}
 * </Button>
 * ```
 */
export function useRunWorkflow(options?: {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}): UseRunWorkflowResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (id: string) => runWorkflow(id),
    onSuccess: () => {
      // Invalidate workflows to refresh status
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
      options?.onSuccess?.();
    },
    onError: (error: Error) => {
      options?.onError?.(error);
    },
  });

  return {
    runWorkflow: async (id: string) => {
      await mutation.mutateAsync(id);
    },
    isRunning: mutation.isPending,
    error: mutation.error,
  };
}

// =============================================================================
// Stop Workflow Mutation
// =============================================================================

interface UseStopWorkflowResult {
  stopWorkflow: (id: string) => Promise<void>;
  isStopping: boolean;
  error: Error | null;
}

/**
 * Hook to stop a running workflow.
 */
export function useStopWorkflow(options?: {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}): UseStopWorkflowResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (id: string) => stopWorkflow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
      options?.onSuccess?.();
    },
    onError: (error: Error) => {
      options?.onError?.(error);
    },
  });

  return {
    stopWorkflow: async (id: string) => {
      await mutation.mutateAsync(id);
    },
    isStopping: mutation.isPending,
    error: mutation.error,
  };
}
