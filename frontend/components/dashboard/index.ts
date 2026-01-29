/**
 * Dashboard components for the Lead-Gen application.
 *
 * @example
 * ```tsx
 * import {
 *   StatsCard,
 *   StatsGrid,
 *   WorkflowCard,
 *   WorkflowsGrid,
 *   RecentActivity,
 * } from '@/components/dashboard';
 * ```
 */

export { StatsCard, StatsCardSkeleton, type StatsCardProps } from "./stats-card";
export { StatsGrid } from "./stats-grid";
export {
  WorkflowCard,
  WorkflowCardSkeleton,
  WorkflowStatusBadge,
  type WorkflowCardProps,
} from "./workflow-card";
export { WorkflowsGrid } from "./workflows-grid";
export { RecentActivity } from "./recent-activity";
