/**
 * Hooks Module - React Query data fetching hooks exports.
 *
 * This module provides centralized data fetching using React Query
 * for the Lead-Gen dashboard application.
 *
 * @example
 * ```tsx
 * // Import hooks
 * import {
 *   useLeads,
 *   useWorkflows,
 *   useSettings,
 *   useDashboard,
 * } from '@/hooks';
 *
 * // Use in components
 * function MyComponent() {
 *   const { data: leads, isLoading } = useLeads({ status: 'new' });
 *   const { stats, activeWorkflows } = useDashboard();
 *
 *   // ...
 * }
 * ```
 *
 * @packageDocumentation
 */

// =============================================================================
// Legacy exports (backward compatibility)
// =============================================================================

export {
  // Dashboard hooks
  useDashboardStats,
  useWorkflows,
  useRunWorkflow,
  useStopWorkflow,
  // Query keys (for cache invalidation)
  dashboardKeys,
  workflowKeys,
} from "./use-dashboard";

// =============================================================================
// Lead Hooks
// =============================================================================

export {
  // Query keys
  leadKeys,

  // Query hooks
  useLeads,
  useLeadsInfinite,
  useLead,
  useEnrichedLead,
  useLeadStats,

  // Mutation hooks
  useCreateLead,
  useUpdateLead,
  useDeleteLead,
  useEnrichLead,
  useExportLeads,

  // Bulk operation hooks
  useBulkUpdateStatus,
  useBulkEnrichLeads,
  useBulkDeleteLeads,
  useBulkAddTags,

  // Prefetch helpers
  prefetchLeads,
  prefetchLead,
} from './useLeads';

// =============================================================================
// New Workflow Hooks (extended)
// =============================================================================

export {
  // Query keys (extended)
  workflowKeys as workflowQueryKeys,

  // Query hooks
  useWorkflow,
  useWorkflowStatus,
  useWorkflowExecutions,

  // Mutation hooks
  useCreateWorkflow,
  useUpdateWorkflow,
  useDeleteWorkflow,
  useDuplicateWorkflow,

  // Execution hooks (new)
  useRunWorkflow as useRunWorkflowMutation,
  useStopWorkflow as useStopWorkflowMutation,
  usePauseWorkflow,
  useResumeWorkflow,

  // Enable/Disable hooks
  useEnableWorkflow,
  useDisableWorkflow,

  // Prefetch helpers
  prefetchWorkflows,
  prefetchWorkflow,
} from './useWorkflows';

// =============================================================================
// Settings Hooks
// =============================================================================

export {
  // Query keys
  settingsKeys,

  // Query hooks
  useSettings,
  useValidateApiKeys,
  useHealthCheck,
  useSystemInfo,

  // Mutation hooks
  useUpdateSettings,
  useResetSettings,
  useUpdateApiKeys,
  useTestApiKey,

  // Prefetch helpers
  prefetchSettings,
  prefetchHealthCheck,
} from './useSettings';

// =============================================================================
// Dashboard Hooks (extended)
// =============================================================================

export {
  // Query keys (extended)
  dashboardKeys as dashboardQueryKeys,

  // Query hooks (new)
  useDashboard,
  useRecentActivity,
  useSummaryStats,

  // Prefetch helpers
  prefetchDashboard,
} from './useDashboard';

export type { DashboardData, SummaryStats } from './useDashboard';
