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
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

// Stats Card Component
function StatsCard({
  title,
  value,
  change,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string;
  change: string;
  icon: React.ElementType;
  trend: "up" | "down" | "neutral";
}) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          <p
            className={`text-xs mt-1 ${
              trend === "up"
                ? "text-green-600"
                : trend === "down"
                ? "text-red-600"
                : "text-muted-foreground"
            }`}
          >
            {change}
          </p>
        </div>
        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
          <Icon className="h-6 w-6 text-primary" />
        </div>
      </div>
    </div>
  );
}

// Recent Activity Component
function RecentActivity() {
  const activities = [
    {
      id: 1,
      type: "scrape",
      message: "Scraped 20 dentists from Bratislava",
      time: "2 min ago",
      status: "success",
    },
    {
      id: 2,
      type: "enrich",
      message: "Enriched 18 leads with emails",
      time: "5 min ago",
      status: "success",
    },
    {
      id: 3,
      type: "generate",
      message: "Generated 15 outreach messages",
      time: "8 min ago",
      status: "success",
    },
    {
      id: 4,
      type: "export",
      message: "Exported to Google Sheets",
      time: "10 min ago",
      status: "success",
    },
    {
      id: 5,
      type: "error",
      message: "Rate limit hit on Hunter.io",
      time: "15 min ago",
      status: "warning",
    },
  ];

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <div className="p-6 border-b">
        <h3 className="font-semibold">Recent Activity</h3>
      </div>
      <div className="divide-y">
        {activities.map((activity) => (
          <div key={activity.id} className="p-4 flex items-center gap-4">
            {activity.status === "success" ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <AlertCircle className="h-5 w-5 text-yellow-600" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium">{activity.message}</p>
              <p className="text-xs text-muted-foreground">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Workflow Card Component
function WorkflowCard({
  name,
  description,
  lastRun,
  status,
}: {
  name: string;
  description: string;
  lastRun: string;
  status: "ready" | "running" | "error";
}) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold">{name}</h4>
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            status === "ready"
              ? "bg-green-100 text-green-700"
              : status === "running"
              ? "bg-blue-100 text-blue-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {status === "ready" ? "Ready" : status === "running" ? "Running" : "Error"}
        </span>
      </div>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {lastRun}
        </span>
        <button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90">
          <Play className="h-4 w-4" />
          Run
        </button>
      </div>
    </div>
  );
}

// Main Dashboard Component
export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold text-primary">Lead-Gen</h1>
          <p className="text-xs text-muted-foreground">Enterprise Dashboard</p>
        </div>
        <nav className="p-4">
          <ul className="space-y-1">
            {[
              { id: "overview", label: "Overview", icon: BarChart3 },
              { id: "leads", label: "Leads", icon: Users },
              { id: "messages", label: "Messages", icon: Mail },
              { id: "workflows", label: "Workflows", icon: Play },
              { id: "exports", label: "Exports", icon: FileSpreadsheet },
              { id: "gdpr", label: "GDPR Center", icon: Shield },
              { id: "settings", label: "Settings", icon: Settings },
            ].map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
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

      {/* Main Content */}
      <main className="flex-1 p-8">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold">Dashboard Overview</h2>
          <p className="text-muted-foreground">
            Welcome back! Here's what's happening with your leads.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total Leads"
            value="1,234"
            change="+12% from last week"
            icon={Users}
            trend="up"
          />
          <StatsCard
            title="Emails Found"
            value="892"
            change="72% enrichment rate"
            icon={Mail}
            trend="up"
          />
          <StatsCard
            title="Messages Sent"
            value="456"
            change="+8% response rate"
            icon={TrendingUp}
            trend="up"
          />
          <StatsCard
            title="API Cost"
            value="$23.45"
            change="This month"
            icon={BarChart3}
            trend="neutral"
          />
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflows */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-lg font-semibold">Active Workflows</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <WorkflowCard
                name="Slovakia Dentists"
                description="Scrape dentists in Slovak cities"
                lastRun="2 hours ago"
                status="ready"
              />
              <WorkflowCard
                name="Austria Doctors"
                description="Scrape doctors in Vienna area"
                lastRun="Yesterday"
                status="ready"
              />
              <WorkflowCard
                name="Czech Clinics"
                description="Scrape clinics in Prague"
                lastRun="Running..."
                status="running"
              />
              <WorkflowCard
                name="Email Enrichment"
                description="Enrich leads with Hunter.io"
                lastRun="1 hour ago"
                status="ready"
              />
            </div>
          </div>

          {/* Activity Feed */}
          <div>
            <RecentActivity />
          </div>
        </div>
      </main>
    </div>
  );
}
