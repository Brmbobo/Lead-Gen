/**
 * useDashboard - Combined React Query hooks for dashboard data.
 *
 * Provides a unified hook for fetching all dashboard-related data:
 * - Lead statistics
 * - Active workflows
 * - Recent activity
 * - System health
 */

import {
  useQuery,
  useQueries,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';

import {
  getDashboardStats,
  getLeadStats,
  getWorkflows,
  getHealthCheck,
} from '@/lib/api';

import type {
  DashboardStats,
  Workflow,
  HealthCheckResponse,
  PaginatedResponse,
  Activity,
  LeadStatus,
} from '@/lib/api/types';

import { leadKeys } from './useLeads';
import { workflowKeys } from './useWorkflows';
import { settingsKeys } from './useSettings';

// =============================================================================
// Query Keys
// =============================================================================

/** Query key factory for dashboard */
export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardKeys.all, 'stats'] as const,
  activity: () => [...dashboardKeys.all, 'activity'] as const,
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

/** Combined dashboard data */
export interface DashboardData {
  /** Dashboard statistics */
  stats: DashboardStats | undefined;

  /** Lead statistics */
  leadStats: LeadStats | undefined;

  /** Active/running workflows */
  activeWorkflows: Workflow[];

  /** System health status */
  health: HealthCheckResponse | undefined;

  /** Recent activity items */
  recentActivity: Activity[];

  /** Loading states */
  isLoading: boolean;
  isStatsLoading: boolean;
  isLeadStatsLoading: boolean;
  isWorkflowsLoading: boolean;
  isHealthLoading: boolean;

  /** Error states */
  hasError: boolean;
  statsError: Error | null;
  leadStatsError: Error | null;
  workflowsError: Error | null;
  healthError: Error | null;

  /** Refresh functions */
  refetchStats: () => void;
  refetchAll: () => void;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook for fetching dashboard statistics.
 *
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: stats, isLoading } = useDashboardStats();
 *
 * if (isLoading) return <Skeleton />;
 *
 * return (
 *   <div>
 *     <h2>Total Leads: {stats?.total_leads}</h2>
 *   </div>
 * );
 * ```
 */
export function useDashboardStats(
  options?: Omit<
    UseQueryOptions<DashboardStats, Error>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: getDashboardStats,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Refetch every minute
    ...options,
  });
}

/**
 * Hook for fetching recent activity.
 *
 * @param limit - Number of activities to fetch
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: activity } = useRecentActivity(10);
 *
 * return (
 *   <ActivityFeed items={activity} />
 * );
 * ```
 */
export function useRecentActivity(
  limit: number = 10,
  options?: Omit<UseQueryOptions<Activity[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: [...dashboardKeys.activity(), limit] as const,
    queryFn: async () => {
      const stats = await getDashboardStats();
      return stats.recent_activities.slice(0, limit);
    },
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Combined hook for all dashboard data.
 *
 * This hook fetches all data needed for the dashboard in parallel
 * and provides a unified interface for loading states and errors.
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const {
 *     stats,
 *     leadStats,
 *     activeWorkflows,
 *     health,
 *     isLoading,
 *     hasError,
 *     refetchAll,
 *   } = useDashboard();
 *
 *   if (isLoading) return <DashboardSkeleton />;
 *   if (hasError) return <ErrorState onRetry={refetchAll} />;
 *
 *   return (
 *     <div>
 *       <StatsCards stats={stats} leadStats={leadStats} />
 *       <WorkflowsList workflows={activeWorkflows} />
 *       <HealthIndicator health={health} />
 *       <ActivityFeed items={stats?.recent_activities ?? []} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useDashboard(): DashboardData {
  const queryClient = useQueryClient();

  // Fetch all dashboard data in parallel
  const results = useQueries({
    queries: [
      {
        queryKey: dashboardKeys.stats(),
        queryFn: getDashboardStats,
        staleTime: 30 * 1000,
        gcTime: 5 * 60 * 1000,
      },
      {
        queryKey: leadKeys.stats(),
        queryFn: getLeadStats,
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
      },
      {
        queryKey: workflowKeys.list({ enabled: true, page_size: 10 }),
        queryFn: () => getWorkflows({ enabled: true, page_size: 10 }),
        staleTime: 30 * 1000,
        gcTime: 5 * 60 * 1000,
      },
      {
        queryKey: settingsKeys.health(),
        queryFn: getHealthCheck,
        staleTime: 30 * 1000,
        gcTime: 60 * 1000,
      },
    ],
  });

  const [statsQuery, leadStatsQuery, workflowsQuery, healthQuery] = results;

  // Compute combined loading state
  const isLoading = results.some((r) => r.isLoading);

  // Compute combined error state
  const hasError = results.some((r) => r.isError);

  // Extract active/running workflows
  const workflowsData = workflowsQuery.data as
    | PaginatedResponse<Workflow>
    | undefined;
  const activeWorkflows = workflowsData?.items?.filter(
    (w) => w.status === 'running' || w.status === 'pending'
  ) ?? [];

  // Extract recent activity from stats
  const statsData = statsQuery.data as DashboardStats | undefined;
  const recentActivity = statsData?.recent_activities ?? [];

  // Refetch functions
  const refetchStats = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.stats() });
  };

  const refetchAll = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    queryClient.invalidateQueries({ queryKey: leadKeys.stats() });
    queryClient.invalidateQueries({
      queryKey: workflowKeys.list({ enabled: true, page_size: 10 }),
    });
    queryClient.invalidateQueries({ queryKey: settingsKeys.health() });
  };

  return {
    // Data
    stats: statsData,
    leadStats: leadStatsQuery.data as LeadStats | undefined,
    activeWorkflows,
    health: healthQuery.data as HealthCheckResponse | undefined,
    recentActivity,

    // Loading states
    isLoading,
    isStatsLoading: statsQuery.isLoading,
    isLeadStatsLoading: leadStatsQuery.isLoading,
    isWorkflowsLoading: workflowsQuery.isLoading,
    isHealthLoading: healthQuery.isLoading,

    // Error states
    hasError,
    statsError: statsQuery.error,
    leadStatsError: leadStatsQuery.error,
    workflowsError: workflowsQuery.error,
    healthError: healthQuery.error,

    // Refresh functions
    refetchStats,
    refetchAll,
  };
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch all dashboard data.
 *
 * Call this on app initialization or before navigating to dashboard.
 *
 * @param queryClient - Query client instance
 *
 * @example
 * ```tsx
 * // In a layout or page
 * const queryClient = useQueryClient();
 *
 * useEffect(() => {
 *   prefetchDashboard(queryClient);
 * }, []);
 * ```
 */
export async function prefetchDashboard(
  queryClient: ReturnType<typeof useQueryClient>
): Promise<void> {
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: dashboardKeys.stats(),
      queryFn: getDashboardStats,
      staleTime: 30 * 1000,
    }),
    queryClient.prefetchQuery({
      queryKey: leadKeys.stats(),
      queryFn: getLeadStats,
      staleTime: 60 * 1000,
    }),
    queryClient.prefetchQuery({
      queryKey: workflowKeys.list({ enabled: true, page_size: 10 }),
      queryFn: () => getWorkflows({ enabled: true, page_size: 10 }),
      staleTime: 30 * 1000,
    }),
    queryClient.prefetchQuery({
      queryKey: settingsKeys.health(),
      queryFn: getHealthCheck,
      staleTime: 30 * 1000,
    }),
  ]);
}

// =============================================================================
// Summary Statistics Hook
// =============================================================================

/** Summary statistics for quick display */
export interface SummaryStats {
  totalLeads: number;
  newLeadsThisWeek: number;
  changePercent: number;
  emailsFound: number;
  enrichmentRate: number;
  messagesSent: number;
  responseRate: number;
  activeWorkflows: number;
  apiCostThisMonth: number;
}

/**
 * Hook for fetching summary statistics only.
 *
 * Lighter than useDashboard when you only need numbers.
 *
 * @example
 * ```tsx
 * const { stats, isLoading } = useSummaryStats();
 *
 * return (
 *   <div>
 *     <Stat label="Total Leads" value={stats.totalLeads} />
 *     <Stat label="Active Workflows" value={stats.activeWorkflows} />
 *   </div>
 * );
 * ```
 */
export function useSummaryStats(): {
  stats: SummaryStats;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const { data, isLoading, error, refetch } = useDashboardStats();

  const stats: SummaryStats = {
    totalLeads: data?.total_leads ?? 0,
    newLeadsThisWeek: data?.leads_this_week ?? 0,
    changePercent: data?.leads_change_percent ?? 0,
    emailsFound: data?.emails_found ?? 0,
    enrichmentRate: data?.email_enrichment_rate ?? 0,
    messagesSent: data?.messages_sent ?? 0,
    responseRate: data?.message_response_rate ?? 0,
    activeWorkflows: data?.active_workflows ?? 0,
    apiCostThisMonth: data?.api_cost_this_month ?? 0,
  };

  return {
    stats,
    isLoading,
    error,
    refetch,
  };
}
