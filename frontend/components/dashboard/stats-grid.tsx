"use client";

import { Users, Mail, TrendingUp, BarChart3, DollarSign } from "lucide-react";
import { StatsCard, StatsCardSkeleton } from "./stats-card";
import { ErrorCard } from "@/components/ui/error-card";
import { useDashboardStats } from "@/hooks";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import type { StatsCardProps } from "./stats-card";

interface StatsGridProps {
  /** Additional CSS classes */
  className?: string;
}

/**
 * Helper to determine trend direction from a numeric value.
 */
function getTrend(
  value: number | undefined | null,
  upThreshold: number,
  downThreshold: number
): StatsCardProps["trend"] {
  if (value === undefined || value === null) return "neutral";
  if (value >= upThreshold) return "up";
  if (value <= downThreshold) return "down";
  return "neutral";
}

/**
 * Helper to determine trend from change percent.
 */
function getChangeTrend(value: number | undefined | null): StatsCardProps["trend"] {
  if (value === undefined || value === null) return "neutral";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "neutral";
}

/**
 * Dashboard statistics grid component.
 *
 * Fetches and displays key metrics:
 * - Total Leads
 * - Emails Found
 * - Messages Sent
 * - API Cost
 *
 * @example
 * ```tsx
 * <StatsGrid />
 * ```
 */
export function StatsGrid({ className }: StatsGridProps): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboardStats();

  if (isError && error) {
    return (
      <div className={cn("mb-8", className)}>
        <ErrorCard
          error={error}
          onRetry={() => refetch()}
          isRetrying={isFetching}
          variant="inline"
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6", className)}>
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
      </div>
    );
  }

  // Calculate derived values
  const leadsChange = data?.leads_change_percent
    ? `${data.leads_change_percent > 0 ? "+" : ""}${formatPercent(data.leads_change_percent)} from last week`
    : undefined;

  const emailRate = data?.email_enrichment_rate
    ? `${formatPercent(data.email_enrichment_rate)} enrichment rate`
    : undefined;

  const responseRate = data?.message_response_rate
    ? `${formatPercent(data.message_response_rate)} response rate`
    : undefined;

  return (
    <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6", className)}>
      <StatsCard
        title="Total Leads"
        value={data?.total_leads ?? 0}
        change={leadsChange}
        icon={Users}
        trend={getChangeTrend(data?.leads_change_percent)}
      />
      <StatsCard
        title="Emails Found"
        value={data?.emails_found ?? 0}
        change={emailRate}
        icon={Mail}
        trend={getTrend(data?.email_enrichment_rate, 70, 50)}
      />
      <StatsCard
        title="Messages Sent"
        value={data?.messages_sent ?? 0}
        change={responseRate}
        icon={TrendingUp}
        trend={getTrend(data?.message_response_rate, 10, 5)}
      />
      <StatsCard
        title="API Cost"
        value={formatCurrency(data?.api_cost_this_month ?? 0)}
        change="This month"
        icon={DollarSign}
        trend="neutral"
        formatValue={false}
      />
    </div>
  );
}
