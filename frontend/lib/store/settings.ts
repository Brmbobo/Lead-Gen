/**
 * Settings Store - Zustand state management for application settings.
 *
 * Manages client-side settings with localStorage persistence:
 * - Theme preferences
 * - Language settings
 * - UI preferences
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { MessageLanguage } from '@/lib/api/types';

// =============================================================================
// Types
// =============================================================================

/** Theme options */
export type Theme = 'light' | 'dark' | 'system';

/** Supported languages */
export type Language = MessageLanguage;

/** Items per page options */
export type ItemsPerPage = 10 | 25 | 50 | 100;

/** Settings store state */
export interface SettingsState {
  /** Current theme */
  theme: Theme;

  /** Current language */
  language: Language;

  /** Sidebar collapsed state */
  sidebarCollapsed: boolean;

  /** Items per page for lists */
  itemsPerPage: ItemsPerPage;

  /** Show onboarding tips */
  showTips: boolean;

  /** Compact mode for tables */
  compactMode: boolean;

  /** Auto-refresh interval in seconds (0 = disabled) */
  autoRefreshInterval: number;

  // Actions
  /** Set theme */
  setTheme: (theme: Theme) => void;

  /** Set language */
  setLanguage: (language: Language) => void;

  /** Toggle sidebar collapsed state */
  toggleSidebar: () => void;

  /** Set sidebar collapsed state */
  setSidebarCollapsed: (collapsed: boolean) => void;

  /** Set items per page */
  setItemsPerPage: (count: ItemsPerPage) => void;

  /** Toggle tips visibility */
  toggleTips: () => void;

  /** Set tips visibility */
  setShowTips: (show: boolean) => void;

  /** Toggle compact mode */
  toggleCompactMode: () => void;

  /** Set compact mode */
  setCompactMode: (compact: boolean) => void;

  /** Set auto-refresh interval */
  setAutoRefreshInterval: (seconds: number) => void;

  /** Reset settings to defaults */
  resetSettings: () => void;
}

// =============================================================================
// Default Values
// =============================================================================

const DEFAULT_SETTINGS: Omit<SettingsState, 'setTheme' | 'setLanguage' | 'toggleSidebar' | 'setSidebarCollapsed' | 'setItemsPerPage' | 'toggleTips' | 'setShowTips' | 'toggleCompactMode' | 'setCompactMode' | 'setAutoRefreshInterval' | 'resetSettings'> = {
  theme: 'system',
  language: 'sk',
  sidebarCollapsed: false,
  itemsPerPage: 25,
  showTips: true,
  compactMode: false,
  autoRefreshInterval: 0,
};

// =============================================================================
// Store
// =============================================================================

/**
 * Settings store with localStorage persistence.
 *
 * @example
 * ```tsx
 * // In a component
 * const { theme, setTheme, language, toggleSidebar } = useSettingsStore();
 *
 * // Change theme
 * setTheme('dark');
 *
 * // Toggle sidebar
 * toggleSidebar();
 * ```
 */
export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        ...DEFAULT_SETTINGS,

        // Actions
        setTheme: (theme: Theme) => {
          set(
            { theme },
            false,
            'settings/setTheme'
          );
        },

        setLanguage: (language: Language) => {
          set(
            { language },
            false,
            'settings/setLanguage'
          );
        },

        toggleSidebar: () => {
          set(
            (state) => ({ sidebarCollapsed: !state.sidebarCollapsed }),
            false,
            'settings/toggleSidebar'
          );
        },

        setSidebarCollapsed: (collapsed: boolean) => {
          set(
            { sidebarCollapsed: collapsed },
            false,
            'settings/setSidebarCollapsed'
          );
        },

        setItemsPerPage: (count: ItemsPerPage) => {
          set(
            { itemsPerPage: count },
            false,
            'settings/setItemsPerPage'
          );
        },

        toggleTips: () => {
          set(
            (state) => ({ showTips: !state.showTips }),
            false,
            'settings/toggleTips'
          );
        },

        setShowTips: (show: boolean) => {
          set(
            { showTips: show },
            false,
            'settings/setShowTips'
          );
        },

        toggleCompactMode: () => {
          set(
            (state) => ({ compactMode: !state.compactMode }),
            false,
            'settings/toggleCompactMode'
          );
        },

        setCompactMode: (compact: boolean) => {
          set(
            { compactMode: compact },
            false,
            'settings/setCompactMode'
          );
        },

        setAutoRefreshInterval: (seconds: number) => {
          set(
            { autoRefreshInterval: Math.max(0, seconds) },
            false,
            'settings/setAutoRefreshInterval'
          );
        },

        resetSettings: () => {
          set(
            { ...DEFAULT_SETTINGS },
            false,
            'settings/resetSettings'
          );
        },
      }),
      {
        name: 'lead-gen-settings',
        version: 1,
        partialize: (state) => ({
          theme: state.theme,
          language: state.language,
          sidebarCollapsed: state.sidebarCollapsed,
          itemsPerPage: state.itemsPerPage,
          showTips: state.showTips,
          compactMode: state.compactMode,
          autoRefreshInterval: state.autoRefreshInterval,
        }),
      }
    ),
    { name: 'settings-store' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/** Get effective theme (resolving 'system' to actual theme) */
export const selectEffectiveTheme = (state: SettingsState): 'light' | 'dark' => {
  if (state.theme === 'system') {
    // Check system preference - this will be evaluated at runtime
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
    }
    return 'light';
  }
  return state.theme;
};

/** Get language display name */
export const selectLanguageDisplayName = (state: SettingsState): string => {
  const names: Record<Language, string> = {
    sk: 'Slovencina',
    cs: 'Cestina',
    en: 'English',
    de: 'Deutsch',
  };
  return names[state.language];
};
