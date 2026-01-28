/**
 * Workflows API functions.
 *
 * Provides type-safe functions for all workflow-related API operations:
 * - List, get, create, update, delete workflows
 * - Run, stop, pause workflows
 * - Get workflow execution status and history
 */

import { apiClient } from './client';
import type {
  Workflow,
  WorkflowInput,
  WorkflowRunConfig,
  WorkflowExecution,
  WorkflowStep,
  WorkflowStatus,
  PaginatedResponse,
  SuccessResponse,
} from './types';

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

/** Workflow execution list parameters */
interface ExecutionListParams {
  page?: number;
  page_size?: number;
  status?: WorkflowStatus;
  workflow_id?: string;
  from_date?: string;
  to_date?: string;
}

/** Workflow validation result */
interface WorkflowValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/** Workflow run response */
interface WorkflowRunResponse {
  execution_id: string;
  workflow_id: string;
  status: WorkflowStatus;
  started_at: string;
  message: string;
}

// =============================================================================
// Workflow CRUD Operations
// =============================================================================

/**
 * Get paginated list of workflows.
 *
 * @param params - Filtering and pagination parameters
 * @returns Paginated list of workflows
 *
 * @example
 * ```ts
 * const { items, total } = await getWorkflows({ enabled: true });
 * ```
 */
export async function getWorkflows(
  params: WorkflowListParams = {}
): Promise<PaginatedResponse<Workflow>> {
  const queryParams: Record<string, string | number | boolean | undefined | string[]> = {
    page: params.page,
    page_size: params.page_size,
    status: params.status,
    enabled: params.enabled,
    search: params.search,
    tags: params.tags,
    sort_by: params.sort_by,
    sort_order: params.sort_order,
  };

  return apiClient.get<PaginatedResponse<Workflow>>('/workflows', queryParams);
}

/**
 * Get a single workflow by ID.
 *
 * @param id - Workflow ID
 * @returns Workflow details
 *
 * @example
 * ```ts
 * const workflow = await getWorkflow('abc123');
 * ```
 */
export async function getWorkflow(id: string): Promise<Workflow> {
  return apiClient.get<Workflow>(`/workflows/${id}`);
}

/**
 * Create a new workflow.
 *
 * @param data - Workflow configuration
 * @returns Created workflow
 *
 * @example
 * ```ts
 * const workflow = await createWorkflow({
 *   name: 'Slovakia Dentists',
 *   steps: [
 *     { name: 'scrape', type: 'scrape', scrape_config: { query: 'zubar', location: 'Bratislava' } },
 *     { name: 'enrich', type: 'enrich', enrich_config: { provider: 'hunter' } },
 *   ],
 * });
 * ```
 */
export async function createWorkflow(data: WorkflowInput): Promise<Workflow> {
  return apiClient.post<Workflow>('/workflows', data);
}

/**
 * Update an existing workflow.
 *
 * @param id - Workflow ID
 * @param data - Updated workflow data
 * @returns Updated workflow
 *
 * @example
 * ```ts
 * const workflow = await updateWorkflow('abc123', { name: 'New Name' });
 * ```
 */
export async function updateWorkflow(
  id: string,
  data: Partial<WorkflowInput>
): Promise<Workflow> {
  return apiClient.patch<Workflow>(`/workflows/${id}`, data);
}

/**
 * Delete a workflow.
 *
 * @param id - Workflow ID
 * @returns Success response
 *
 * @example
 * ```ts
 * await deleteWorkflow('abc123');
 * ```
 */
export async function deleteWorkflow(id: string): Promise<SuccessResponse> {
  return apiClient.delete<SuccessResponse>(`/workflows/${id}`);
}

/**
 * Duplicate a workflow.
 *
 * @param id - Workflow ID to duplicate
 * @param newName - Name for the duplicated workflow
 * @returns Duplicated workflow
 */
export async function duplicateWorkflow(id: string, newName?: string): Promise<Workflow> {
  return apiClient.post<Workflow>(`/workflows/${id}/duplicate`, { name: newName });
}

// =============================================================================
// Workflow Execution Operations
// =============================================================================

/**
 * Run a workflow.
 *
 * @param id - Workflow ID
 * @param config - Optional run configuration overrides
 * @returns Execution info
 *
 * @example
 * ```ts
 * const execution = await runWorkflow('abc123', { max_leads: 50 });
 * ```
 */
export async function runWorkflow(
  id: string,
  config: WorkflowRunConfig = {}
): Promise<WorkflowRunResponse> {
  return apiClient.post<WorkflowRunResponse>(`/workflows/${id}/run`, config);
}

/**
 * Stop a running workflow.
 *
 * @param id - Workflow ID
 * @returns Success response
 *
 * @example
 * ```ts
 * await stopWorkflow('abc123');
 * ```
 */
export async function stopWorkflow(id: string): Promise<SuccessResponse> {
  return apiClient.post<SuccessResponse>(`/workflows/${id}/stop`);
}

/**
 * Pause a running workflow.
 *
 * @param id - Workflow ID
 * @returns Success response
 */
export async function pauseWorkflow(id: string): Promise<SuccessResponse> {
  return apiClient.post<SuccessResponse>(`/workflows/${id}/pause`);
}

/**
 * Resume a paused workflow.
 *
 * @param id - Workflow ID
 * @returns Success response
 */
export async function resumeWorkflow(id: string): Promise<SuccessResponse> {
  return apiClient.post<SuccessResponse>(`/workflows/${id}/resume`);
}

/**
 * Get current workflow status.
 *
 * @param id - Workflow ID
 * @returns Current execution status
 *
 * @example
 * ```ts
 * const status = await getWorkflowStatus('abc123');
 * console.log(status.current_step, status.progress_percent);
 * ```
 */
export async function getWorkflowStatus(id: string): Promise<{
  status: WorkflowStatus;
  current_step: string | null;
  current_step_index: number;
  total_steps: number;
  progress_percent: number;
  leads_processed: number;
  error_message: string | null;
  started_at: string | null;
  estimated_completion: string | null;
}> {
  return apiClient.get(`/workflows/${id}/status`);
}

// =============================================================================
// Workflow Execution History
// =============================================================================

/**
 * Get workflow execution history.
 *
 * @param id - Workflow ID
 * @param params - Pagination parameters
 * @returns Paginated list of executions
 */
export async function getWorkflowExecutions(
  id: string,
  params: Omit<ExecutionListParams, 'workflow_id'> = {}
): Promise<PaginatedResponse<WorkflowExecution>> {
  return apiClient.get<PaginatedResponse<WorkflowExecution>>(
    `/workflows/${id}/executions`,
    params
  );
}

/**
 * Get all executions across workflows.
 *
 * @param params - Filter and pagination parameters
 * @returns Paginated list of executions
 */
export async function getAllExecutions(
  params: ExecutionListParams = {}
): Promise<PaginatedResponse<WorkflowExecution>> {
  return apiClient.get<PaginatedResponse<WorkflowExecution>>('/executions', params);
}

/**
 * Get a specific execution by ID.
 *
 * @param executionId - Execution ID
 * @returns Execution details
 */
export async function getExecution(executionId: string): Promise<WorkflowExecution> {
  return apiClient.get<WorkflowExecution>(`/executions/${executionId}`);
}

/**
 * Get execution logs.
 *
 * @param executionId - Execution ID
 * @param stepId - Optional step ID to filter logs
 * @returns Array of log entries
 */
export async function getExecutionLogs(
  executionId: string,
  stepId?: string
): Promise<Array<{
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  step_id: string | null;
  message: string;
  metadata?: Record<string, unknown>;
}>> {
  return apiClient.get(`/executions/${executionId}/logs`, { step_id: stepId });
}

// =============================================================================
// Workflow Validation
// =============================================================================

/**
 * Validate a workflow configuration.
 *
 * @param data - Workflow configuration to validate
 * @returns Validation result
 *
 * @example
 * ```ts
 * const validation = await validateWorkflow(workflowConfig);
 * if (!validation.valid) {
 *   console.error('Validation errors:', validation.errors);
 * }
 * ```
 */
export async function validateWorkflow(data: WorkflowInput): Promise<WorkflowValidation> {
  return apiClient.post<WorkflowValidation>('/workflows/validate', data);
}

/**
 * Validate a single workflow step.
 *
 * @param step - Step configuration to validate
 * @returns Validation result
 */
export async function validateStep(step: Partial<WorkflowStep>): Promise<WorkflowValidation> {
  return apiClient.post<WorkflowValidation>('/workflows/validate-step', step);
}

// =============================================================================
// Workflow Enable/Disable
// =============================================================================

/**
 * Enable a workflow.
 *
 * @param id - Workflow ID
 * @returns Updated workflow
 */
export async function enableWorkflow(id: string): Promise<Workflow> {
  return apiClient.post<Workflow>(`/workflows/${id}/enable`);
}

/**
 * Disable a workflow.
 *
 * @param id - Workflow ID
 * @returns Updated workflow
 */
export async function disableWorkflow(id: string): Promise<Workflow> {
  return apiClient.post<Workflow>(`/workflows/${id}/disable`);
}

// =============================================================================
// Workflow Import/Export
// =============================================================================

/**
 * Export workflow as YAML.
 *
 * @param id - Workflow ID
 * @returns YAML string
 */
export async function exportWorkflowYAML(id: string): Promise<string> {
  return apiClient.get<string>(`/workflows/${id}/export`, undefined, {
    headers: { Accept: 'text/yaml' },
  });
}

/**
 * Import workflow from YAML.
 *
 * @param yaml - YAML string
 * @returns Created workflow
 */
export async function importWorkflowYAML(yaml: string): Promise<Workflow> {
  return apiClient.post<Workflow>('/workflows/import', { yaml });
}

/**
 * Import workflow from YAML file.
 *
 * @param file - YAML file
 * @returns Created workflow
 */
export async function importWorkflowFile(file: File): Promise<Workflow> {
  return apiClient.uploadFile<Workflow>('/workflows/import-file', file, 'file');
}

// =============================================================================
// Workflow Templates
// =============================================================================

/**
 * Get available workflow templates.
 *
 * @returns List of workflow templates
 */
export async function getWorkflowTemplates(): Promise<Array<{
  id: string;
  name: string;
  description: string;
  tags: string[];
  steps_count: number;
}>> {
  return apiClient.get('/workflows/templates');
}

/**
 * Create workflow from template.
 *
 * @param templateId - Template ID
 * @param name - Name for the new workflow
 * @returns Created workflow
 */
export async function createFromTemplate(
  templateId: string,
  name: string
): Promise<Workflow> {
  return apiClient.post<Workflow>('/workflows/from-template', {
    template_id: templateId,
    name,
  });
}

// =============================================================================
// Workflow Scheduling
// =============================================================================

/**
 * Update workflow schedule.
 *
 * @param id - Workflow ID
 * @param cronExpression - Cron expression for scheduling
 * @returns Updated workflow
 *
 * @example
 * ```ts
 * // Run every day at 9am
 * await updateWorkflowSchedule('abc123', '0 9 * * *');
 * ```
 */
export async function updateWorkflowSchedule(
  id: string,
  cronExpression: string
): Promise<Workflow> {
  return apiClient.patch<Workflow>(`/workflows/${id}/schedule`, {
    schedule_cron: cronExpression,
  });
}

/**
 * Remove workflow schedule.
 *
 * @param id - Workflow ID
 * @returns Updated workflow
 */
export async function removeWorkflowSchedule(id: string): Promise<Workflow> {
  return apiClient.patch<Workflow>(`/workflows/${id}/schedule`, {
    schedule_cron: '',
  });
}

/**
 * Get upcoming scheduled runs.
 *
 * @param id - Workflow ID
 * @param count - Number of upcoming runs to return
 * @returns Array of scheduled run times
 */
export async function getUpcomingRuns(
  id: string,
  count: number = 5
): Promise<Array<{ scheduled_at: string; workflow_id: string }>> {
  return apiClient.get(`/workflows/${id}/upcoming-runs`, { count });
}
