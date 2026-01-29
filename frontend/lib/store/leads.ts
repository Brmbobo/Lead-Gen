/**
 * Leads Store - Zustand state management for leads.
 *
 * Manages client-side lead state including:
 * - Selected leads for bulk operations
 * - Filter and sort preferences
 * - UI state for lead interactions
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { LeadStatus, LeadSource } from '@/lib/api/types';

// =============================================================================
// Types
// =============================================================================

/** Filter configuration for leads */
export interface LeadFilters {
  status?: LeadStatus;
  source?: LeadSource;
  businessType?: string;
  city?: string;
  minQualityScore?: number;
  search?: string;
  tags?: string[];
}

/** Sort field options */
export type LeadSortField = 'name' | 'scraped_at' | 'quality_score' | 'status';

/** Leads store state */
export interface LeadsState {
  /** Currently selected lead IDs for bulk operations */
  selectedLeads: string[];

  /** Current filter configuration */
  filters: LeadFilters;

  /** Current sort field */
  sortBy: LeadSortField;

  /** Sort direction */
  sortOrder: 'asc' | 'desc';

  /** Currently expanded lead ID (for detail view) */
  expandedLeadId: string | null;

  // Actions
  /** Select a single lead */
  selectLead: (id: string) => void;

  /** Deselect a single lead */
  deselectLead: (id: string) => void;

  /** Toggle lead selection */
  toggleLeadSelection: (id: string) => void;

  /** Select all leads from provided IDs */
  selectAll: (ids: string[]) => void;

  /** Clear all selections */
  clearSelection: () => void;

  /** Set filter values (partial update) */
  setFilters: (filters: Partial<LeadFilters>) => void;

  /** Reset filters to defaults */
  resetFilters: () => void;

  /** Set sort configuration */
  setSort: (sortBy: LeadSortField, sortOrder?: 'asc' | 'desc') => void;

  /** Toggle sort order */
  toggleSortOrder: () => void;

  /** Set expanded lead */
  setExpandedLead: (id: string | null) => void;

  /** Check if a lead is selected */
  isSelected: (id: string) => boolean;
}

// =============================================================================
// Default Values
// =============================================================================

const DEFAULT_FILTERS: LeadFilters = {
  status: undefined,
  source: undefined,
  businessType: undefined,
  city: undefined,
  minQualityScore: undefined,
  search: undefined,
  tags: undefined,
};

// =============================================================================
// Store
// =============================================================================

/**
 * Leads store for managing lead selection, filtering, and sorting state.
 *
 * @example
 * ```tsx
 * // In a component
 * const { selectedLeads, selectLead, clearSelection } = useLeadsStore();
 *
 * // Select a lead
 * selectLead('lead-123');
 *
 * // Check selection count
 * console.log(`${selectedLeads.length} leads selected`);
 * ```
 */
export const useLeadsStore = create<LeadsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      selectedLeads: [],
      filters: { ...DEFAULT_FILTERS },
      sortBy: 'scraped_at',
      sortOrder: 'desc',
      expandedLeadId: null,

      // Actions
      selectLead: (id: string) => {
        set(
          (state) => ({
            selectedLeads: state.selectedLeads.includes(id)
              ? state.selectedLeads
              : [...state.selectedLeads, id],
          }),
          false,
          'leads/selectLead'
        );
      },

      deselectLead: (id: string) => {
        set(
          (state) => ({
            selectedLeads: state.selectedLeads.filter((leadId) => leadId !== id),
          }),
          false,
          'leads/deselectLead'
        );
      },

      toggleLeadSelection: (id: string) => {
        const { selectedLeads } = get();
        if (selectedLeads.includes(id)) {
          get().deselectLead(id);
        } else {
          get().selectLead(id);
        }
      },

      selectAll: (ids: string[]) => {
        set(
          { selectedLeads: [...ids] },
          false,
          'leads/selectAll'
        );
      },

      clearSelection: () => {
        set(
          { selectedLeads: [] },
          false,
          'leads/clearSelection'
        );
      },

      setFilters: (filters: Partial<LeadFilters>) => {
        set(
          (state) => ({
            filters: { ...state.filters, ...filters },
          }),
          false,
          'leads/setFilters'
        );
      },

      resetFilters: () => {
        set(
          { filters: { ...DEFAULT_FILTERS } },
          false,
          'leads/resetFilters'
        );
      },

      setSort: (sortBy: LeadSortField, sortOrder?: 'asc' | 'desc') => {
        set(
          (state) => ({
            sortBy,
            sortOrder: sortOrder ?? state.sortOrder,
          }),
          false,
          'leads/setSort'
        );
      },

      toggleSortOrder: () => {
        set(
          (state) => ({
            sortOrder: state.sortOrder === 'asc' ? 'desc' : 'asc',
          }),
          false,
          'leads/toggleSortOrder'
        );
      },

      setExpandedLead: (id: string | null) => {
        set(
          { expandedLeadId: id },
          false,
          'leads/setExpandedLead'
        );
      },

      isSelected: (id: string) => {
        return get().selectedLeads.includes(id);
      },
    }),
    { name: 'leads-store' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/** Get the count of selected leads */
export const selectSelectedCount = (state: LeadsState): number =>
  state.selectedLeads.length;

/** Check if any leads are selected */
export const selectHasSelection = (state: LeadsState): boolean =>
  state.selectedLeads.length > 0;

/** Get current filter count (number of active filters) */
export const selectActiveFilterCount = (state: LeadsState): number => {
  let count = 0;
  if (state.filters.status) count++;
  if (state.filters.source) count++;
  if (state.filters.businessType) count++;
  if (state.filters.city) count++;
  if (state.filters.minQualityScore) count++;
  if (state.filters.search) count++;
  if (state.filters.tags && state.filters.tags.length > 0) count++;
  return count;
};

/** Check if filters are applied */
export const selectHasFilters = (state: LeadsState): boolean =>
  selectActiveFilterCount(state) > 0;
