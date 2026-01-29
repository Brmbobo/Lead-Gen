"use client";

import * as React from "react";
import { CheckCircle2, AlertCircle, Info, Workflow, FileSpreadsheet, Mail, Search } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { SkeletonActivityItem } from "@/components/ui/skeleton";
import { EmptyActivity } from "@/components/ui/empty-state";
import { ErrorCard } from "@/components/ui/error-card";
import { useDashboardStats } from "@/hooks";
import type { Activity } from "@/lib/api";

interface RecentActivityProps {
  /** Maximum number of items to show */
  maxItems?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Recent activity feed component.
 *
 * Displays a list of recent actions and events with status indicators.
 *
 * @example
 * ```tsx
 * <RecentActivity maxItems={5} />
 * ```
 */
export function RecentActivity({
  maxItems = 5,
  className,
}: RecentActivityProps): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboardStats();

  const activities = data?.recent_activities?.slice(0, maxItems) ?? [];

  return (
    <div className={cn("rounded-lg border bg-card shadow-sm", className)}>
      <div className="p-6 border-b">
        <h3 className="font-semibold">Recent Activity</h3>
      </div>
      <div className="divide-y">
        {isError && error ? (
          <div className="p-4">
            <ErrorCard
              error={error}
              onRetry={() => refetch()}
              isRetrying={isFetching}
              variant="minimal"
            />
          </div>
        ) : isLoading ? (
          <>
            {Array.from({ length: maxItems }).map((_, i) => (
              <SkeletonActivityItem key={i} />
            ))}
          </>
        ) : activities.length === 0 ? (
          <EmptyActivity />
        ) : (
          activities.map((activity) => (
            <ActivityItem key={activity.id} activity={activity} />
          ))
        )}
      </div>
    </div>
  );
}

/**
 * Single activity item component.
 */
function ActivityItem({ activity }: { activity: Activity }): JSX.Element {
  const Icon = getActivityIcon(activity.type);
  const statusColor = getStatusColor(activity.status);

  return (
    <div className="p-4 flex items-center gap-4 hover:bg-muted/50 transition-colors">
      <div className={cn("p-1.5 rounded-full", statusColor.bg)}>
        <Icon className={cn("h-4 w-4", statusColor.text)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{activity.message}</p>
        <p className="text-xs text-muted-foreground">
          {formatRelativeTime(activity.timestamp)}
        </p>
      </div>
      <ActivityStatusBadge status={activity.status} />
    </div>
  );
}

/**
 * Activity status badge component.
 */
function ActivityStatusBadge({
  status,
}: {
  status: Activity["status"];
}): JSX.Element | null {
  const statusConfig = {
    success: {
      label: "Success",
      className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    warning: {
      label: "Warning",
      className: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    },
    error: {
      label: "Error",
      className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
  };

  const config = statusConfig[status];

  // Only show badge for non-success statuses
  if (status === "success") {
    return null;
  }

  return (
    <span
      className={cn(
        "px-2 py-0.5 rounded-full text-xs font-medium",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}

/**
 * Get icon for activity type.
 */
function getActivityIcon(
  type: Activity["type"]
): React.ComponentType<{ className?: string }> {
  const iconMap: Record<Activity["type"], React.ComponentType<{ className?: string }>> = {
    scrape: Search,
    enrich: Mail,
    generate: FileSpreadsheet,
    export: FileSpreadsheet,
    error: AlertCircle,
    workflow: Workflow,
  };

  return iconMap[type] || Info;
}

/**
 * Get status colors.
 */
function getStatusColor(status: Activity["status"]): {
  bg: string;
  text: string;
} {
  const colorMap: Record<Activity["status"], { bg: string; text: string }> = {
    success: {
      bg: "bg-green-100 dark:bg-green-900/30",
      text: "text-green-600 dark:text-green-400",
    },
    warning: {
      bg: "bg-yellow-100 dark:bg-yellow-900/30",
      text: "text-yellow-600 dark:text-yellow-400",
    },
    error: {
      bg: "bg-red-100 dark:bg-red-900/30",
      text: "text-red-600 dark:text-red-400",
    },
  };

  return colorMap[status];
}
