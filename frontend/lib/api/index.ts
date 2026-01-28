/**
 * Lead-Gen API Client Module
 *
 * This module provides a complete, type-safe API client for the Lead-Gen
 * backend services. It includes:
 *
 * - Type definitions matching Python Pydantic models
 * - Error handling with typed errors
 * - Base API client with interceptors
 * - Domain-specific API functions for leads, workflows, and settings
 *
 * @example
 * ```ts
 * // Import specific functions
 * import { getLeads, runWorkflow, getSettings } from '@/lib/api';
 *
 * // Use the API
 * const leads = await getLeads({ status: 'new', page: 1 });
 * await runWorkflow('workflow-id');
 * const settings = await getSettings();
 * ```
 *
 * @example
 * ```ts
 * // Import the API client for custom requests
 * import { apiClient } from '@/lib/api';
 *
 * const data = await apiClient.get<CustomType>('/custom-endpoint');
 * ```
 *
 * @example
 * ```ts
 * // Handle errors
 * import { getLeads, isApiError, ErrorCode } from '@/lib/api';
 *
 * try {
 *   const leads = await getLeads();
 * } catch (error) {
 *   if (isApiError(error)) {
 *     if (error.code === ErrorCode.UNAUTHORIZED) {
 *       // Handle auth error
 *     }
 *     console.error(error.getUserMessage());
 *   }
 * }
 * ```
 *
 * @packageDocumentation
 */

// =============================================================================
// Re-export Types
// =============================================================================

export type {
  // Enums
  LeadSource,
  LeadStatus,
  WorkflowStatus,
  StepType,
  MessageLanguage,
  MessageTone,
  MessageType,
  ExportDestination,
  EnrichmentProvider,

  // Location & Metrics
  Location,
  OpeningHours,
  BusinessMetrics,

  // GDPR
  GDPRConsent,

  // Lead Models
  EmailEnrichment,
  Lead,
  EnrichedLead,
  LeadInput,
  LeadListParams,
  LeadExportParams,

  // Workflow Models
  RetryPolicy,
  RateLimitPolicy,
  ScrapeConfig,
  EnrichConfig,
  GenerateConfig,
  ExportConfig,
  FilterConfig,
  WorkflowStep,
  Workflow,
  WorkflowInput,
  WorkflowRunConfig,
  WorkflowExecution,
  WorkflowStepResult,

  // Outreach Models
  PersonalizationContext,
  MessageTemplate,
  OutreachMessage,

  // Settings Models
  ApiKeyConfig,
  Settings,
  SettingsInput,
  ApiKeyValidation,

  // API Response Types
  PaginatedResponse,
  ApiErrorResponse,
  SuccessResponse,
  HealthCheckResponse,
  DashboardStats,
  Activity,
} from './types';

// =============================================================================
// Re-export Errors
// =============================================================================

export {
  ApiError,
  ErrorCode,
  isApiError,
  isErrorCode,
  isNetworkError,
  isAuthError,
  isRetryableError,
  withErrorHandling,
  getErrorMessage,
  createValidationError,
} from './errors';

export type { ErrorCodeType } from './errors';

// =============================================================================
// Re-export Client
// =============================================================================

export { ApiClient, apiClient } from './client';

export type { ApiClientConfig, RequestConfig } from './client';

// =============================================================================
// Re-export Leads API
// =============================================================================

export {
  // CRUD
  getLeads,
  getLead,
  getEnrichedLead,
  createLead,
  updateLead,
  deleteLead,

  // Status
  updateLeadStatus,
  bulkUpdateStatus,

  // Export
  exportLeads,
  exportToCSV,
  exportToJSON,
  exportToSheets,

  // Stats
  getLeadStats,

  // Enrichment
  enrichLead,
  bulkEnrichLeads,

  // Tags
  addLeadTags,
  removeLeadTags,

  // Bulk
  bulkDeleteLeads,
  bulkAddTags,

  // GDPR
  exportLeadGDPR,
  deleteLeadGDPR,
  pseudonymizeLead,
} from './leads';

// =============================================================================
// Re-export Workflows API
// =============================================================================

export {
  // CRUD
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  duplicateWorkflow,

  // Execution
  runWorkflow,
  stopWorkflow,
  pauseWorkflow,
  resumeWorkflow,
  getWorkflowStatus,

  // History
  getWorkflowExecutions,
  getAllExecutions,
  getExecution,
  getExecutionLogs,

  // Validation
  validateWorkflow,
  validateStep,

  // Enable/Disable
  enableWorkflow,
  disableWorkflow,

  // Import/Export
  exportWorkflowYAML,
  importWorkflowYAML,
  importWorkflowFile,

  // Templates
  getWorkflowTemplates,
  createFromTemplate,

  // Scheduling
  updateWorkflowSchedule,
  removeWorkflowSchedule,
  getUpcomingRuns,
} from './workflows';

// =============================================================================
// Re-export Settings API
// =============================================================================

export {
  // Settings
  getSettings,
  updateSettings,
  resetSettings,

  // API Keys
  updateApiKeys,
  validateApiKeys,
  testApiKey,
  removeApiKey,

  // Health
  getHealthCheck,
  getSystemInfo,
  getDashboardStats,

  // Google Sheets
  uploadSheetsCredentials,
  getSheetsAuthUrl,
  completeSheetsAuth,
  listSpreadsheets,

  // Export
  getExportFields,
  updateExportConfig,

  // GDPR
  getGDPRSettings,
  updateGDPRSettings,

  // Rate Limits
  getRateLimits,
  updateRateLimits,

  // UI
  getUIPreferences,
  updateUIPreferences,
  setTheme,
  setLanguage,
} from './settings';
