/**
 * UI Store - Zustand state management for UI state.
 *
 * Manages transient UI state including:
 * - Modal visibility
 * - Notifications/toasts
 * - Loading states
 * - Panel states
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// =============================================================================
// Types
// =============================================================================

/** Notification types */
export type NotificationType = 'success' | 'info' | 'warning' | 'error';

/** Notification object */
export interface Notification {
  /** Unique notification ID */
  id: string;

  /** Notification type */
  type: NotificationType;

  /** Notification title */
  title: string;

  /** Optional description/message */
  message?: string;

  /** Auto-dismiss duration in milliseconds (0 = no auto-dismiss) */
  duration?: number;

  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };

  /** Timestamp when notification was created */
  createdAt: number;
}

/** Modal configuration */
export interface ModalConfig {
  /** Modal ID */
  id: string;

  /** Optional modal data/props */
  data?: Record<string, unknown>;
}

/** Command palette state */
export interface CommandPaletteState {
  isOpen: boolean;
  query: string;
}

/** UI store state */
export interface UIState {
  /** Currently active modal (null if none) */
  activeModal: ModalConfig | null;

  /** Stack of open modals (for nested modals) */
  modalStack: ModalConfig[];

  /** Active notifications */
  notifications: Notification[];

  /** Global loading state */
  isLoading: boolean;

  /** Loading state for specific operations */
  loadingStates: Record<string, boolean>;

  /** Command palette state */
  commandPalette: CommandPaletteState;

  /** Help panel visibility */
  helpPanelOpen: boolean;

  /** Keyboard shortcuts visible */
  showShortcutsHelp: boolean;

  // Actions
  /** Open a modal */
  openModal: (id: string, data?: Record<string, unknown>) => void;

  /** Close current modal */
  closeModal: () => void;

  /** Close a specific modal */
  closeModalById: (id: string) => void;

  /** Close all modals */
  closeAllModals: () => void;

  /** Add a notification */
  addNotification: (
    notification: Omit<Notification, 'id' | 'createdAt'>
  ) => string;

  /** Remove a notification by ID */
  removeNotification: (id: string) => void;

  /** Clear all notifications */
  clearNotifications: () => void;

  /** Set global loading state */
  setLoading: (loading: boolean) => void;

  /** Set loading state for a specific operation */
  setOperationLoading: (operation: string, loading: boolean) => void;

  /** Check if an operation is loading */
  isOperationLoading: (operation: string) => boolean;

  /** Open command palette */
  openCommandPalette: () => void;

  /** Close command palette */
  closeCommandPalette: () => void;

  /** Toggle command palette */
  toggleCommandPalette: () => void;

  /** Set command palette query */
  setCommandPaletteQuery: (query: string) => void;

  /** Toggle help panel */
  toggleHelpPanel: () => void;

  /** Set help panel visibility */
  setHelpPanelOpen: (open: boolean) => void;

  /** Toggle shortcuts help */
  toggleShortcutsHelp: () => void;
}

// =============================================================================
// Utilities
// =============================================================================

/** Generate a unique notification ID */
function generateNotificationId(): string {
  return `notification-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// =============================================================================
// Store
// =============================================================================

/**
 * UI store for managing transient UI state.
 *
 * @example
 * ```tsx
 * // In a component
 * const { openModal, addNotification, isLoading } = useUIStore();
 *
 * // Open a modal
 * openModal('confirm-delete', { leadId: '123' });
 *
 * // Show a notification
 * addNotification({
 *   type: 'success',
 *   title: 'Lead deleted',
 *   message: 'The lead has been removed.',
 *   duration: 3000,
 * });
 * ```
 */
export const useUIStore = create<UIState>()(
  devtools(
    (set, get) => ({
      // Initial state
      activeModal: null,
      modalStack: [],
      notifications: [],
      isLoading: false,
      loadingStates: {},
      commandPalette: {
        isOpen: false,
        query: '',
      },
      helpPanelOpen: false,
      showShortcutsHelp: false,

      // Actions
      openModal: (id: string, data?: Record<string, unknown>) => {
        const modal: ModalConfig = { id, data };
        set(
          (state) => ({
            activeModal: modal,
            modalStack: state.activeModal
              ? [...state.modalStack, state.activeModal]
              : state.modalStack,
          }),
          false,
          'ui/openModal'
        );
      },

      closeModal: () => {
        set(
          (state) => {
            const previousModal = state.modalStack[state.modalStack.length - 1];
            return {
              activeModal: previousModal ?? null,
              modalStack: state.modalStack.slice(0, -1),
            };
          },
          false,
          'ui/closeModal'
        );
      },

      closeModalById: (id: string) => {
        set(
          (state) => ({
            activeModal:
              state.activeModal?.id === id ? null : state.activeModal,
            modalStack: state.modalStack.filter((m) => m.id !== id),
          }),
          false,
          'ui/closeModalById'
        );
      },

      closeAllModals: () => {
        set(
          { activeModal: null, modalStack: [] },
          false,
          'ui/closeAllModals'
        );
      },

      addNotification: (notification) => {
        const id = generateNotificationId();
        const fullNotification: Notification = {
          ...notification,
          id,
          createdAt: Date.now(),
          duration: notification.duration ?? 5000,
        };

        set(
          (state) => ({
            notifications: [...state.notifications, fullNotification],
          }),
          false,
          'ui/addNotification'
        );

        // Auto-dismiss if duration is set
        if (fullNotification.duration && fullNotification.duration > 0) {
          setTimeout(() => {
            get().removeNotification(id);
          }, fullNotification.duration);
        }

        return id;
      },

      removeNotification: (id: string) => {
        set(
          (state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          }),
          false,
          'ui/removeNotification'
        );
      },

      clearNotifications: () => {
        set(
          { notifications: [] },
          false,
          'ui/clearNotifications'
        );
      },

      setLoading: (loading: boolean) => {
        set(
          { isLoading: loading },
          false,
          'ui/setLoading'
        );
      },

      setOperationLoading: (operation: string, loading: boolean) => {
        set(
          (state) => ({
            loadingStates: {
              ...state.loadingStates,
              [operation]: loading,
            },
          }),
          false,
          'ui/setOperationLoading'
        );
      },

      isOperationLoading: (operation: string) => {
        return get().loadingStates[operation] ?? false;
      },

      openCommandPalette: () => {
        set(
          { commandPalette: { isOpen: true, query: '' } },
          false,
          'ui/openCommandPalette'
        );
      },

      closeCommandPalette: () => {
        set(
          { commandPalette: { isOpen: false, query: '' } },
          false,
          'ui/closeCommandPalette'
        );
      },

      toggleCommandPalette: () => {
        set(
          (state) => ({
            commandPalette: {
              isOpen: !state.commandPalette.isOpen,
              query: state.commandPalette.isOpen ? '' : state.commandPalette.query,
            },
          }),
          false,
          'ui/toggleCommandPalette'
        );
      },

      setCommandPaletteQuery: (query: string) => {
        set(
          (state) => ({
            commandPalette: { ...state.commandPalette, query },
          }),
          false,
          'ui/setCommandPaletteQuery'
        );
      },

      toggleHelpPanel: () => {
        set(
          (state) => ({ helpPanelOpen: !state.helpPanelOpen }),
          false,
          'ui/toggleHelpPanel'
        );
      },

      setHelpPanelOpen: (open: boolean) => {
        set(
          { helpPanelOpen: open },
          false,
          'ui/setHelpPanelOpen'
        );
      },

      toggleShortcutsHelp: () => {
        set(
          (state) => ({ showShortcutsHelp: !state.showShortcutsHelp }),
          false,
          'ui/toggleShortcutsHelp'
        );
      },
    }),
    { name: 'ui-store' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/** Get count of active notifications */
export const selectNotificationCount = (state: UIState): number =>
  state.notifications.length;

/** Check if any modal is open */
export const selectHasOpenModal = (state: UIState): boolean =>
  state.activeModal !== null;

/** Get current modal ID */
export const selectCurrentModalId = (state: UIState): string | null =>
  state.activeModal?.id ?? null;

/** Get notifications by type */
export const selectNotificationsByType = (
  state: UIState,
  type: NotificationType
): Notification[] => state.notifications.filter((n) => n.type === type);

/** Check if any loading operation is active */
export const selectHasActiveLoadingOperations = (state: UIState): boolean =>
  state.isLoading || Object.values(state.loadingStates).some(Boolean);

// =============================================================================
// Notification Helpers
// =============================================================================

/**
 * Helper function to show a success notification.
 *
 * @example
 * ```ts
 * showSuccess('Lead created successfully');
 * ```
 */
export function showSuccess(title: string, message?: string): string {
  return useUIStore.getState().addNotification({
    type: 'success',
    title,
    message,
    duration: 3000,
  });
}

/**
 * Helper function to show an info notification.
 *
 * @example
 * ```ts
 * showInfo('Processing...', 'This may take a moment');
 * ```
 */
export function showInfo(title: string, message?: string): string {
  return useUIStore.getState().addNotification({
    type: 'info',
    title,
    message,
    duration: 5000,
  });
}

/**
 * Helper function to show a warning notification.
 *
 * @example
 * ```ts
 * showWarning('API quota low', 'Consider upgrading your plan');
 * ```
 */
export function showWarning(title: string, message?: string): string {
  return useUIStore.getState().addNotification({
    type: 'warning',
    title,
    message,
    duration: 7000,
  });
}

/**
 * Helper function to show an error notification.
 *
 * @example
 * ```ts
 * showError('Failed to save', 'Please try again later');
 * ```
 */
export function showError(title: string, message?: string): string {
  return useUIStore.getState().addNotification({
    type: 'error',
    title,
    message,
    duration: 0, // Errors don't auto-dismiss
  });
}
