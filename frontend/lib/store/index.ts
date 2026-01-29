/**
 * Store Module - Zustand state management exports.
 *
 * This module provides centralized state management using Zustand
 * for the Lead-Gen dashboard application.
 *
 * @example
 * ```tsx
 * // Import stores
 * import {
 *   useLeadsStore,
 *   useWorkflowsStore,
 *   useSettingsStore,
 *   useUIStore,
 * } from '@/lib/store';
 *
 * // Use in components
 * function MyComponent() {
 *   const { selectedLeads, selectLead } = useLeadsStore();
 *   const { theme, setTheme } = useSettingsStore();
 *   const { addNotification } = useUIStore();
 *
 *   // ...
 * }
 * ```
 *
 * @packageDocumentation
 */

// =============================================================================
// Leads Store
// =============================================================================

export {
  useLeadsStore,
  selectSelectedCount,
  selectHasSelection,
  selectActiveFilterCount,
  selectHasFilters,
} from './leads';

export type {
  LeadsState,
  LeadFilters,
  LeadSortField,
} from './leads';

// =============================================================================
// Workflows Store
// =============================================================================

export {
  useWorkflowsStore,
  selectRunningCount,
  selectHasRunningWorkflows,
  selectAllProgress,
  selectRunningProgress,
} from './workflows';

export type {
  WorkflowsState,
  WorkflowProgress,
} from './workflows';

// =============================================================================
// Settings Store
// =============================================================================

export {
  useSettingsStore,
  selectEffectiveTheme,
  selectLanguageDisplayName,
} from './settings';

export type {
  SettingsState,
  Theme,
  Language,
  ItemsPerPage,
} from './settings';

// =============================================================================
// UI Store
// =============================================================================

export {
  useUIStore,
  selectNotificationCount,
  selectHasOpenModal,
  selectCurrentModalId,
  selectNotificationsByType,
  selectHasActiveLoadingOperations,
  // Notification helpers
  showSuccess,
  showInfo,
  showWarning,
  showError,
} from './ui';

export type {
  UIState,
  Notification,
  NotificationType,
  ModalConfig,
  CommandPaletteState,
} from './ui';
