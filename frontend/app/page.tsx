"use client";

import { useState } from "react";
import {
  BarChart3,
  Users,
  Mail,
  FileSpreadsheet,
  Play,
  Settings,
  Shield,
} from "lucide-react";
import { StatsGrid, WorkflowsGrid, RecentActivity } from "@/components/dashboard";
import { ErrorBoundary } from "@/components/ui/error-boundary";

// =============================================================================
// Navigation Configuration
// =============================================================================

const navItems = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "leads", label: "Leads", icon: Users },
  { id: "messages", label: "Messages", icon: Mail },
  { id: "workflows", label: "Workflows", icon: Play },
  { id: "exports", label: "Exports", icon: FileSpreadsheet },
  { id: "gdpr", label: "GDPR Center", icon: Shield },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

type TabId = (typeof navItems)[number]["id"];

// =============================================================================
// Sidebar Component
// =============================================================================

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

function Sidebar({ activeTab, onTabChange }: SidebarProps): JSX.Element {
  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      <div className="p-6 border-b">
        <h1 className="text-xl font-bold text-primary">Lead-Gen</h1>
        <p className="text-xs text-muted-foreground">Enterprise Dashboard</p>
      </div>
      <nav className="p-4 flex-1">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === item.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

// =============================================================================
// Dashboard Header Component
// =============================================================================

function DashboardHeader(): JSX.Element {
  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold">Dashboard Overview</h2>
      <p className="text-muted-foreground">
        Welcome back! Here is what is happening with your leads.
      </p>
    </div>
  );
}

// =============================================================================
// Overview Tab Content
// =============================================================================

function OverviewContent(): JSX.Element {
  return (
    <>
      {/* Stats Grid */}
      <StatsGrid className="mb-8" />

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workflows */}
        <div className="lg:col-span-2">
          <WorkflowsGrid maxItems={4} />
        </div>

        {/* Activity Feed */}
        <div>
          <RecentActivity maxItems={5} />
        </div>
      </div>
    </>
  );
}

// =============================================================================
// Placeholder Components for Other Tabs
// =============================================================================

function ComingSoonPlaceholder({ title }: { title: string }): JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
        <Settings className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm">
        This section is under development. Check back soon for updates.
      </p>
    </div>
  );
}

// =============================================================================
// Main Dashboard Component
// =============================================================================

export default function Dashboard(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const renderContent = (): JSX.Element => {
    switch (activeTab) {
      case "overview":
        return <OverviewContent />;
      case "leads":
        return <ComingSoonPlaceholder title="Leads Management" />;
      case "messages":
        return <ComingSoonPlaceholder title="Messages & Outreach" />;
      case "workflows":
        return <ComingSoonPlaceholder title="Workflow Management" />;
      case "exports":
        return <ComingSoonPlaceholder title="Data Exports" />;
      case "gdpr":
        return <ComingSoonPlaceholder title="GDPR Compliance Center" />;
      case "settings":
        return <ComingSoonPlaceholder title="Settings" />;
      default:
        return <OverviewContent />;
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">
        <DashboardHeader />
        <ErrorBoundary>
          {renderContent()}
        </ErrorBoundary>
      </main>
    </div>
  );
}
