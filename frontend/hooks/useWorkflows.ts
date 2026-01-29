/**
 * useWorkflows - React Query hooks for workflow data fetching.
 *
 * Provides type-safe hooks for:
 * - Fetching workflows (list, single)
 * - Workflow mutations (create, update, delete)
 * - Workflow execution (run, stop, pause, resume)
 * - Workflow status polling
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';

import {
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  runWorkflow,
  stopWorkflow,
  pauseWorkflow,
  resumeWorkflow,
  getWorkflowStatus,
  getWorkflowExecutions,
  duplicateWorkflow,
  enableWorkflow,
  disableWorkflow,
} from '@/lib/api';

import type {
  Workflow,
  WorkflowInput,
  WorkflowRunConfig,
  WorkflowExecution,
  WorkflowStatus,
  PaginatedResponse,
  SuccessResponse,
} from '@/lib/api/types';

import { useWorkflowsStore, type WorkflowProgress } from '@/lib/store';

// =============================================================================
// Query Keys
// =============================================================================

/** Query key factory for workflows */
export const workflowKeys = {
  all: ['workflows'] as const,
  lists: () => [...workflowKeys.all, 'list'] as const,
  list: (params: WorkflowListParams) => [...workflowKeys.lists(), params] as const,
  details: () => [...workflowKeys.all, 'detail'] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
  status: (id: string) => [...workflowKeys.detail(id), 'status'] as const,
  executions: (id: string) => [...workflowKeys.detail(id), 'executions'] as const,
};

// =============================================================================
// Types
// =============================================================================

/** Workflow list parameters */
interface WorkflowListParams {
  page?: number;
  page_size?: number;
  status?: WorkflowStatus;
  enabled?: boolean;
  search?: string;
  tags?: string[];
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'status';
  sort_order?: 'asc' | 'desc';
}

/** Workflow run response */
interface WorkflowRunResponse {
  execution_id: string;
  workflow_id: string;
  status: WorkflowStatus;
  started_at: string;
  message: string;
}

/** Workflow status response */
interface WorkflowStatusResponse {
  status: WorkflowStatus;
  current_step: string | null;
  current_step_index: number;
  total_steps: number;
  progress_percent: number;
  leads_processed: number;
  error_message: string | null;
  started_at: string | null;
  estimated_completion: string | null;
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook for fetching paginated workflows.
 *
 * @param params - Filter and pagination parameters
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useWorkflows({ enabled: true });
 *
 * if (isLoading) return <Loading />;
 *
 * return <WorkflowList workflows={data.items} />;
 * ```
 */
export function useWorkflows(
  params?: WorkflowListParams,
  options?: Omit<
    UseQueryOptions<PaginatedResponse<Workflow>, Error>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: workflowKeys.list(params ?? {}),
    queryFn: () => getWorkflows(params),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * Hook for fetching a single workflow.
 *
 * @param id - Workflow ID
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: workflow } = useWorkflow('workflow-123');
 * console.log(workflow?.steps);
 * ```
 */
export function useWorkflow(
  id: string,
  options?: Omit<UseQueryOptions<Workflow, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => getWorkflow(id),
    enabled: !!id,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
}

/**
 * Hook for polling workflow status.
 *
 * @param id - Workflow ID
 * @param enabled - Whether polling is enabled
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { isRunning } = useWorkflowsStore();
 * const { data: status } = useWorkflowStatus('workflow-123', isRunning('workflow-123'));
 *
 * if (status?.status === 'running') {
 *   console.log(`Progress: ${status.progress_percent}%`);
 * }
 * ```
 */
export function useWorkflowStatus(
  id: string,
  enabled: boolean = false,
  options?: Omit<
    UseQueryOptions<WorkflowStatusResponse, Error>,
    'queryKey' | 'queryFn' | 'enabled' | 'refetchInterval'
  >
) {
  const updateProgress = useWorkflowsStore((state) => state.updateProgress);
  const removeRunning = useWorkflowsStore((state) => state.removeRunning);

  return useQuery({
    queryKey: workflowKeys.status(id),
    queryFn: () => getWorkflowStatus(id),
    enabled: !!id && enabled,
    refetchInterval: (query) => {
      // Poll every 2 seconds while running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000;
      }
      return false;
    },
    staleTime: 0, // Always fetch fresh status
    gcTime: 30 * 1000, // 30 seconds
    ...options,
    // Update store on successful fetch
    select: (data) => {
      // Update workflow progress in store
      const progress: WorkflowProgress = {
        workflowId: id,
        status: data.status,
        currentStep: data.current_step,
        currentStepIndex: data.current_step_index,
        totalSteps: data.total_steps,
        progressPercent: data.progress_percent,
        leadsProcessed: data.leads_processed,
        startedAt: data.started_at ?? new Date().toISOString(),
        estimatedCompletion: data.estimated_completion,
        errorMessage: data.error_message,
      };
      updateProgress(progress);

      // Remove from running if completed
      if (
        data.status === 'completed' ||
        data.status === 'failed' ||
        data.status === 'cancelled'
      ) {
        removeRunning(id);
      }

      return data;
    },
  });
}

/**
 * Hook for fetching workflow execution history.
 *
 * @param id - Workflow ID
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: executions } = useWorkflowExecutions('workflow-123');
 * ```
 */
export function useWorkflowExecutions(
  id: string,
  options?: Omit<
    UseQueryOptions<PaginatedResponse<WorkflowExecution>, Error>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: workflowKeys.executions(id),
    queryFn: () => getWorkflowExecutions(id),
    enabled: !!id,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    ...options,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook for creating a new workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: create } = useCreateWorkflow();
 *
 * create({
 *   name: 'My Workflow',
 *   steps: [{ type: 'scrape', name: 'Scrape', scrape_config: {...} }],
 * });
 * ```
 */
export function useCreateWorkflow(
  options?: UseMutationOptions<Workflow, Error, WorkflowInput>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createWorkflow,
    onSuccess: (newWorkflow) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.setQueryData(workflowKeys.detail(newWorkflow.id), newWorkflow);
    },
    ...options,
  });
}

/**
 * Hook for updating a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: update } = useUpdateWorkflow();
 *
 * update({ id: 'workflow-123', data: { name: 'Updated Name' } });
 * ```
 */
export function useUpdateWorkflow(
  options?: UseMutationOptions<
    Workflow,
    Error,
    { id: string; data: Partial<WorkflowInput> }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateWorkflow(id, data),
    onSuccess: (updatedWorkflow) => {
      queryClient.setQueryData(
        workflowKeys.detail(updatedWorkflow.id),
        updatedWorkflow
      );
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook for deleting a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: remove } = useDeleteWorkflow();
 *
 * remove('workflow-123');
 * ```
 */
export function useDeleteWorkflow(
  options?: UseMutationOptions<SuccessResponse, Error, string>
) {
  const queryClient = useQueryClient();
  const selectWorkflow = useWorkflowsStore((state) => state.selectWorkflow);

  return useMutation({
    mutationFn: deleteWorkflow,
    onSuccess: (_, deletedId) => {
      queryClient.removeQueries({ queryKey: workflowKeys.detail(deletedId) });
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      selectWorkflow(null);
    },
    ...options,
  });
}

/**
 * Hook for duplicating a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: duplicate } = useDuplicateWorkflow();
 *
 * duplicate({ id: 'workflow-123', newName: 'Copy of Workflow' });
 * ```
 */
export function useDuplicateWorkflow(
  options?: UseMutationOptions<
    Workflow,
    Error,
    { id: string; newName?: string }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, newName }) => duplicateWorkflow(id, newName),
    onSuccess: (newWorkflow) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.setQueryData(workflowKeys.detail(newWorkflow.id), newWorkflow);
    },
    ...options,
  });
}

// =============================================================================
// Execution Hooks
// =============================================================================

/**
 * Hook for running a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: run, isPending } = useRunWorkflow();
 *
 * run({ id: 'workflow-123', config: { max_leads: 50 } });
 * ```
 */
export function useRunWorkflow(
  options?: UseMutationOptions<
    WorkflowRunResponse,
    Error,
    { id: string; config?: WorkflowRunConfig }
  >
) {
  const queryClient = useQueryClient();
  const addRunning = useWorkflowsStore((state) => state.addRunning);

  return useMutation({
    mutationFn: ({ id, config }) => runWorkflow(id, config),
    onSuccess: (response, { id }) => {
      addRunning(id);
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: workflowKeys.executions(id) });
    },
    ...options,
  });
}

/**
 * Hook for stopping a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: stop } = useStopWorkflow();
 *
 * stop('workflow-123');
 * ```
 */
export function useStopWorkflow(
  options?: UseMutationOptions<SuccessResponse, Error, string>
) {
  const queryClient = useQueryClient();
  const removeRunning = useWorkflowsStore((state) => state.removeRunning);
  const clearProgress = useWorkflowsStore((state) => state.clearProgress);

  return useMutation({
    mutationFn: stopWorkflow,
    onSuccess: (_, id) => {
      removeRunning(id);
      clearProgress(id);
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(id) });
    },
    ...options,
  });
}

/**
 * Hook for pausing a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: pause } = usePauseWorkflow();
 *
 * pause('workflow-123');
 * ```
 */
export function usePauseWorkflow(
  options?: UseMutationOptions<SuccessResponse, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: pauseWorkflow,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(id) });
    },
    ...options,
  });
}

/**
 * Hook for resuming a paused workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: resume } = useResumeWorkflow();
 *
 * resume('workflow-123');
 * ```
 */
export function useResumeWorkflow(
  options?: UseMutationOptions<SuccessResponse, Error, string>
) {
  const queryClient = useQueryClient();
  const addRunning = useWorkflowsStore((state) => state.addRunning);

  return useMutation({
    mutationFn: resumeWorkflow,
    onSuccess: (_, id) => {
      addRunning(id);
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(id) });
    },
    ...options,
  });
}

// =============================================================================
// Enable/Disable Hooks
// =============================================================================

/**
 * Hook for enabling a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: enable } = useEnableWorkflow();
 *
 * enable('workflow-123');
 * ```
 */
export function useEnableWorkflow(
  options?: UseMutationOptions<Workflow, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: enableWorkflow,
    onSuccess: (updatedWorkflow) => {
      queryClient.setQueryData(
        workflowKeys.detail(updatedWorkflow.id),
        updatedWorkflow
      );
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook for disabling a workflow.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: disable } = useDisableWorkflow();
 *
 * disable('workflow-123');
 * ```
 */
export function useDisableWorkflow(
  options?: UseMutationOptions<Workflow, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: disableWorkflow,
    onSuccess: (updatedWorkflow) => {
      queryClient.setQueryData(
        workflowKeys.detail(updatedWorkflow.id),
        updatedWorkflow
      );
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch workflows data.
 *
 * @param queryClient - Query client instance
 * @param params - Fetch parameters
 */
export async function prefetchWorkflows(
  queryClient: ReturnType<typeof useQueryClient>,
  params: WorkflowListParams = {}
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: workflowKeys.list(params),
    queryFn: () => getWorkflows(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Prefetch a single workflow.
 *
 * @param queryClient - Query client instance
 * @param id - Workflow ID
 */
export async function prefetchWorkflow(
  queryClient: ReturnType<typeof useQueryClient>,
  id: string
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => getWorkflow(id),
    staleTime: 60 * 1000,
  });
}
