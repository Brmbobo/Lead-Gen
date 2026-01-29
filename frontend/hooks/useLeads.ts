/**
 * useLeads - React Query hooks for lead data fetching.
 *
 * Provides type-safe hooks for:
 * - Fetching leads (paginated, single, enriched)
 * - Lead mutations (create, update, delete, enrich)
 * - Lead statistics
 * - Bulk operations
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
  type UseQueryOptions,
  type UseMutationOptions,
  type UseInfiniteQueryOptions,
} from '@tanstack/react-query';

import {
  getLeads,
  getLead,
  getEnrichedLead,
  getLeadStats,
  createLead,
  updateLead,
  deleteLead,
  enrichLead,
  exportLeads,
  bulkUpdateStatus,
  bulkEnrichLeads,
  bulkDeleteLeads,
  bulkAddTags,
} from '@/lib/api';

import type {
  Lead,
  EnrichedLead,
  LeadInput,
  LeadListParams,
  LeadExportParams,
  LeadStatus,
  PaginatedResponse,
  SuccessResponse,
} from '@/lib/api/types';

import { useLeadsStore } from '@/lib/store';

// =============================================================================
// Query Keys
// =============================================================================

/** Query key factory for leads */
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (params: LeadListParams) => [...leadKeys.lists(), params] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
  enriched: (id: string) => [...leadKeys.detail(id), 'enriched'] as const,
  stats: () => [...leadKeys.all, 'stats'] as const,
};

// =============================================================================
// Types
// =============================================================================

/** Lead stats response */
interface LeadStats {
  total: number;
  by_status: Record<LeadStatus, number>;
  by_source: Record<string, number>;
  avg_quality_score: number;
  with_email: number;
  with_phone: number;
}

/** Bulk operation result */
interface BulkOperationResult {
  success: boolean;
  processed: number;
  failed: number;
  errors: Array<{ id: string; error: string }>;
}

/** Export response types */
interface SheetsExportResponse {
  success: boolean;
  spreadsheet_url: string;
  rows_exported: number;
}

interface FileExportResponse {
  success: boolean;
  download_url: string;
  filename: string;
  rows_exported: number;
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook for fetching paginated leads.
 *
 * @param params - Filter and pagination parameters
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useLeads({ status: 'new', page: 1 });
 *
 * if (isLoading) return <Loading />;
 * if (error) return <Error message={error.message} />;
 *
 * return <LeadsList leads={data.items} />;
 * ```
 */
export function useLeads(
  params?: LeadListParams,
  options?: Omit<
    UseQueryOptions<PaginatedResponse<Lead>, Error>,
    'queryKey' | 'queryFn'
  >
) {
  const store = useLeadsStore();

  // Merge store filters with params
  const mergedParams: LeadListParams = {
    ...params,
    status: params?.status ?? store.filters.status,
    source: params?.source ?? store.filters.source,
    business_type: params?.business_type ?? store.filters.businessType,
    city: params?.city ?? store.filters.city,
    min_quality_score: params?.min_quality_score ?? store.filters.minQualityScore,
    search: params?.search ?? store.filters.search,
    tags: params?.tags ?? store.filters.tags,
    sort_by: params?.sort_by ?? store.sortBy,
    sort_order: params?.sort_order ?? store.sortOrder,
  };

  return useQuery({
    queryKey: leadKeys.list(mergedParams),
    queryFn: () => getLeads(mergedParams),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
    ...options,
  });
}

/**
 * Hook for infinite scrolling leads list.
 *
 * @param params - Filter parameters (page will be managed automatically)
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const {
 *   data,
 *   fetchNextPage,
 *   hasNextPage,
 *   isFetchingNextPage,
 * } = useLeadsInfinite({ status: 'new' });
 *
 * // Load more
 * if (hasNextPage) {
 *   fetchNextPage();
 * }
 * ```
 */
export function useLeadsInfinite(
  params?: Omit<LeadListParams, 'page'>,
  options?: Omit<
    UseInfiniteQueryOptions<PaginatedResponse<Lead>, Error>,
    'queryKey' | 'queryFn' | 'getNextPageParam' | 'initialPageParam'
  >
) {
  return useInfiniteQuery({
    queryKey: [...leadKeys.lists(), 'infinite', params] as const,
    queryFn: ({ pageParam }) =>
      getLeads({ ...params, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Hook for fetching a single lead.
 *
 * @param id - Lead ID
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: lead, isLoading } = useLead('lead-123');
 * ```
 */
export function useLead(
  id: string,
  options?: Omit<UseQueryOptions<Lead, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => getLead(id),
    enabled: !!id,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
}

/**
 * Hook for fetching an enriched lead.
 *
 * @param id - Lead ID
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: enrichedLead } = useEnrichedLead('lead-123');
 * console.log(enrichedLead?.enrichments);
 * ```
 */
export function useEnrichedLead(
  id: string,
  options?: Omit<UseQueryOptions<EnrichedLead, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: leadKeys.enriched(id),
    queryFn: () => getEnrichedLead(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    ...options,
  });
}

/**
 * Hook for fetching lead statistics.
 *
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: stats } = useLeadStats();
 * console.log(`Total leads: ${stats?.total}`);
 * ```
 */
export function useLeadStats(
  options?: Omit<UseQueryOptions<LeadStats, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: leadKeys.stats(),
    queryFn: getLeadStats,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook for creating a new lead.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: create, isPending } = useCreateLead();
 *
 * create({
 *   name: 'New Business',
 *   phone: '+421900123456',
 * });
 * ```
 */
export function useCreateLead(
  options?: UseMutationOptions<Lead, Error, LeadInput>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createLead,
    onSuccess: (newLead) => {
      // Invalidate leads list
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });

      // Optionally add to cache
      queryClient.setQueryData(leadKeys.detail(newLead.id), newLead);
    },
    ...options,
  });
}

/**
 * Hook for updating a lead.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: update } = useUpdateLead();
 *
 * update({ id: 'lead-123', data: { status: 'contacted' } });
 * ```
 */
export function useUpdateLead(
  options?: UseMutationOptions<Lead, Error, { id: string; data: Partial<LeadInput> }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateLead(id, data),
    onSuccess: (updatedLead) => {
      // Update cache
      queryClient.setQueryData(leadKeys.detail(updatedLead.id), updatedLead);

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });
    },
    ...options,
  });
}

/**
 * Hook for deleting a lead.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: remove } = useDeleteLead();
 *
 * remove('lead-123');
 * ```
 */
export function useDeleteLead(
  options?: UseMutationOptions<SuccessResponse, Error, string>
) {
  const queryClient = useQueryClient();
  const clearSelection = useLeadsStore((state) => state.clearSelection);

  return useMutation({
    mutationFn: deleteLead,
    onSuccess: (_, deletedId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: leadKeys.detail(deletedId) });

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });

      // Clear selection if deleted lead was selected
      clearSelection();
    },
    ...options,
  });
}

/**
 * Hook for enriching a lead.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: enrich, isPending } = useEnrichLead();
 *
 * enrich('lead-123');
 * ```
 */
export function useEnrichLead(
  options?: UseMutationOptions<EnrichedLead, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: enrichLead,
    onSuccess: (enrichedLead, leadId) => {
      // Update both regular and enriched cache
      queryClient.setQueryData(leadKeys.detail(leadId), enrichedLead);
      queryClient.setQueryData(leadKeys.enriched(leadId), enrichedLead);

      // Invalidate lists and stats
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });
    },
    ...options,
  });
}

/**
 * Hook for exporting leads.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: exportData } = useExportLeads();
 *
 * exportData({ format: 'csv', status: ['new', 'enriched'] });
 * ```
 */
export function useExportLeads(
  options?: UseMutationOptions<
    SheetsExportResponse | FileExportResponse,
    Error,
    LeadExportParams
  >
) {
  return useMutation({
    mutationFn: exportLeads,
    ...options,
  });
}

// =============================================================================
// Bulk Operation Hooks
// =============================================================================

/**
 * Hook for bulk updating lead statuses.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: bulkUpdate } = useBulkUpdateStatus();
 * const { selectedLeads } = useLeadsStore();
 *
 * bulkUpdate({ ids: selectedLeads, status: 'contacted' });
 * ```
 */
export function useBulkUpdateStatus(
  options?: UseMutationOptions<
    BulkOperationResult,
    Error,
    { ids: string[]; status: LeadStatus }
  >
) {
  const queryClient = useQueryClient();
  const clearSelection = useLeadsStore((state) => state.clearSelection);

  return useMutation({
    mutationFn: ({ ids, status }) => bulkUpdateStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });
      clearSelection();
    },
    ...options,
  });
}

/**
 * Hook for bulk enriching leads.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: bulkEnrich } = useBulkEnrichLeads();
 * const { selectedLeads } = useLeadsStore();
 *
 * bulkEnrich(selectedLeads);
 * ```
 */
export function useBulkEnrichLeads(
  options?: UseMutationOptions<BulkOperationResult, Error, string[]>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bulkEnrichLeads,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
    },
    ...options,
  });
}

/**
 * Hook for bulk deleting leads.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: bulkDelete } = useBulkDeleteLeads();
 * const { selectedLeads } = useLeadsStore();
 *
 * bulkDelete(selectedLeads);
 * ```
 */
export function useBulkDeleteLeads(
  options?: UseMutationOptions<BulkOperationResult, Error, string[]>
) {
  const queryClient = useQueryClient();
  const clearSelection = useLeadsStore((state) => state.clearSelection);

  return useMutation({
    mutationFn: bulkDeleteLeads,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.stats() });
      clearSelection();
    },
    ...options,
  });
}

/**
 * Hook for bulk adding tags to leads.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: addTags } = useBulkAddTags();
 * const { selectedLeads } = useLeadsStore();
 *
 * addTags({ ids: selectedLeads, tags: ['vip', 'priority'] });
 * ```
 */
export function useBulkAddTags(
  options?: UseMutationOptions<
    BulkOperationResult,
    Error,
    { ids: string[]; tags: string[] }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids, tags }) => bulkAddTags(ids, tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
    },
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch leads data.
 *
 * @param queryClient - Query client instance
 * @param params - Fetch parameters
 *
 * @example
 * ```tsx
 * // In a parent component
 * const queryClient = useQueryClient();
 *
 * // Prefetch for next page
 * prefetchLeads(queryClient, { page: 2 });
 * ```
 */
export async function prefetchLeads(
  queryClient: ReturnType<typeof useQueryClient>,
  params: LeadListParams = {}
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: leadKeys.list(params),
    queryFn: () => getLeads(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Prefetch a single lead.
 *
 * @param queryClient - Query client instance
 * @param id - Lead ID
 *
 * @example
 * ```tsx
 * // Prefetch on hover
 * onMouseEnter={() => prefetchLead(queryClient, lead.id)}
 * ```
 */
export async function prefetchLead(
  queryClient: ReturnType<typeof useQueryClient>,
  id: string
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => getLead(id),
    staleTime: 60 * 1000,
  });
}
