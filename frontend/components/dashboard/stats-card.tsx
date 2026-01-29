"use client";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from "lucide-react";

export interface StatsCardProps {
  /** Card title */
  title: string;
  /** Main value to display */
  value: string | number;
  /** Change indicator text */
  change?: string;
  /** Trend direction */
  trend?: "up" | "down" | "neutral";
  /** Icon component */
  icon: LucideIcon;
  /** Whether data is loading */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Whether to format value as number */
  formatValue?: boolean;
}

/**
 * Statistics card component for dashboard metrics.
 *
 * Supports loading states with skeleton animation.
 *
 * @example
 * ```tsx
 * <StatsCard
 *   title="Total Leads"
 *   value={1234}
 *   change="+12% from last week"
 *   trend="up"
 *   icon={Users}
 *   isLoading={isLoading}
 * />
 * ```
 */
export function StatsCard({
  title,
  value,
  change,
  trend = "neutral",
  icon: Icon,
  isLoading = false,
  className,
  formatValue = true,
}: StatsCardProps): JSX.Element {
  // Format numeric values
  const displayValue =
    formatValue && typeof value === "number"
      ? new Intl.NumberFormat("sk-SK").format(value)
      : value;

  if (isLoading) {
    return <StatsCardSkeleton className={className} />;
  }

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-6 shadow-sm transition-shadow hover:shadow-md",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold tracking-tight">{displayValue}</p>
          {change && (
            <div className="flex items-center gap-1">
              <TrendIndicator trend={trend} />
              <p
                className={cn(
                  "text-xs",
                  trend === "up" && "text-green-600 dark:text-green-400",
                  trend === "down" && "text-red-600 dark:text-red-400",
                  trend === "neutral" && "text-muted-foreground"
                )}
              >
                {change}
              </p>
            </div>
          )}
        </div>
        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
          <Icon className="h-6 w-6 text-primary" />
        </div>
      </div>
    </div>
  );
}

/**
 * Trend indicator icon component.
 */
function TrendIndicator({ trend }: { trend: "up" | "down" | "neutral" }): JSX.Element {
  if (trend === "up") {
    return <TrendingUp className="h-3 w-3 text-green-600 dark:text-green-400" />;
  }
  if (trend === "down") {
    return <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />;
  }
  return <Minus className="h-3 w-3 text-muted-foreground" />;
}

/**
 * Skeleton loading state for StatsCard.
 */
export function StatsCardSkeleton({
  className,
}: {
  className?: string;
}): JSX.Element {
  return (
    <div className={cn("rounded-lg border bg-card p-6 shadow-sm", className)}>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>
    </div>
  );
}
