/**
 * Workflows Store - Zustand state management for workflows.
 *
 * Manages client-side workflow state including:
 * - Running workflow tracking
 * - Selected workflow for editing
 * - Workflow execution progress
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { WorkflowStatus } from '@/lib/api/types';

// =============================================================================
// Types
// =============================================================================

/** Workflow progress information */
export interface WorkflowProgress {
  workflowId: string;
  status: WorkflowStatus;
  currentStep: string | null;
  currentStepIndex: number;
  totalSteps: number;
  progressPercent: number;
  leadsProcessed: number;
  startedAt: string;
  estimatedCompletion: string | null;
  errorMessage: string | null;
}

/** Workflows store state */
export interface WorkflowsState {
  /** IDs of currently running workflows */
  runningWorkflows: string[];

  /** Map of workflow progress data */
  workflowProgress: Record<string, WorkflowProgress>;

  /** Currently selected workflow ID (for editing/viewing) */
  selectedWorkflow: string | null;

  /** Workflow currently being edited in builder */
  editingWorkflowId: string | null;

  // Actions
  /** Add a workflow to running list */
  addRunning: (id: string) => void;

  /** Remove a workflow from running list */
  removeRunning: (id: string) => void;

  /** Select a workflow */
  selectWorkflow: (id: string | null) => void;

  /** Set the editing workflow */
  setEditingWorkflow: (id: string | null) => void;

  /** Update workflow progress */
  updateProgress: (progress: WorkflowProgress) => void;

  /** Clear workflow progress */
  clearProgress: (id: string) => void;

  /** Check if a workflow is running */
  isRunning: (id: string) => boolean;

  /** Get progress for a workflow */
  getProgress: (id: string) => WorkflowProgress | undefined;
}

// =============================================================================
// Store
// =============================================================================

/**
 * Workflows store for managing workflow execution state.
 *
 * @example
 * ```tsx
 * // In a component
 * const { runningWorkflows, addRunning, isRunning } = useWorkflowsStore();
 *
 * // Start tracking a workflow
 * addRunning('workflow-123');
 *
 * // Check if running
 * if (isRunning('workflow-123')) {
 *   console.log('Workflow is executing...');
 * }
 * ```
 */
export const useWorkflowsStore = create<WorkflowsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      runningWorkflows: [],
      workflowProgress: {},
      selectedWorkflow: null,
      editingWorkflowId: null,

      // Actions
      addRunning: (id: string) => {
        set(
          (state) => ({
            runningWorkflows: state.runningWorkflows.includes(id)
              ? state.runningWorkflows
              : [...state.runningWorkflows, id],
          }),
          false,
          'workflows/addRunning'
        );
      },

      removeRunning: (id: string) => {
        set(
          (state) => ({
            runningWorkflows: state.runningWorkflows.filter(
              (workflowId) => workflowId !== id
            ),
          }),
          false,
          'workflows/removeRunning'
        );
      },

      selectWorkflow: (id: string | null) => {
        set(
          { selectedWorkflow: id },
          false,
          'workflows/selectWorkflow'
        );
      },

      setEditingWorkflow: (id: string | null) => {
        set(
          { editingWorkflowId: id },
          false,
          'workflows/setEditingWorkflow'
        );
      },

      updateProgress: (progress: WorkflowProgress) => {
        set(
          (state) => ({
            workflowProgress: {
              ...state.workflowProgress,
              [progress.workflowId]: progress,
            },
            // Automatically track as running if status is running
            runningWorkflows:
              progress.status === 'running' &&
              !state.runningWorkflows.includes(progress.workflowId)
                ? [...state.runningWorkflows, progress.workflowId]
                : progress.status !== 'running' && progress.status !== 'pending'
                ? state.runningWorkflows.filter(
                    (id) => id !== progress.workflowId
                  )
                : state.runningWorkflows,
          }),
          false,
          'workflows/updateProgress'
        );
      },

      clearProgress: (id: string) => {
        set(
          (state) => {
            const { [id]: _, ...remainingProgress } = state.workflowProgress;
            return {
              workflowProgress: remainingProgress,
              runningWorkflows: state.runningWorkflows.filter(
                (workflowId) => workflowId !== id
              ),
            };
          },
          false,
          'workflows/clearProgress'
        );
      },

      isRunning: (id: string) => {
        return get().runningWorkflows.includes(id);
      },

      getProgress: (id: string) => {
        return get().workflowProgress[id];
      },
    }),
    { name: 'workflows-store' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/** Get count of running workflows */
export const selectRunningCount = (state: WorkflowsState): number =>
  state.runningWorkflows.length;

/** Check if any workflow is running */
export const selectHasRunningWorkflows = (state: WorkflowsState): boolean =>
  state.runningWorkflows.length > 0;

/** Get all workflow progress entries */
export const selectAllProgress = (
  state: WorkflowsState
): WorkflowProgress[] => Object.values(state.workflowProgress);

/** Get running workflow progress only */
export const selectRunningProgress = (
  state: WorkflowsState
): WorkflowProgress[] =>
  Object.values(state.workflowProgress).filter(
    (p) => p.status === 'running' || p.status === 'pending'
  );
