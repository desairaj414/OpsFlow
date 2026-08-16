"use client";

import { useEffect, useMemo, useState } from "react";
import { Menu } from "lucide-react";
import Sidebar from "@/components/Sidebar.jsx";
import Overview from "@/components/Overview.jsx";
import { LogoMark } from "@/components/Logo.jsx";
import OpsBoard from "@/components/OpsBoard.jsx";
import Tickets from "@/components/Tickets.jsx";
import IncidentWorkspace from "@/components/IncidentWorkspace.jsx";
import DriftQueue from "@/components/DriftQueue.jsx";
import AutonomyLadder from "@/components/AutonomyLadder.jsx";
import NotificationBell from "@/components/NotificationBell.jsx";
import ChatWidget from "@/components/ChatWidget.jsx";
import { Button } from "@/components/ui/button";
import { cn, decodeJwtPayload } from "@/lib/utils";
import { TAB_INFO } from "@/lib/tabInfo";
import { TAB_PERMISSIONS, ROLE_LABELS } from "@/lib/roles";
import { useAlertStream } from "@/hooks/useAlertStream";
import { useWorkflowRun } from "@/hooks/useWorkflowRun";
import { useTickets } from "@/hooks/useTickets";
import { useAutoTriage } from "@/hooks/useAutoTriage";
import { apiFetch } from "@/lib/api.js";

const TABS = ["Overview", "Ops Board", "Tickets", "Incident Workspace", "Autonomy Ladder"];

function TabInfoBanner({ tab }) {
  const info = TAB_INFO[tab];
  if (!info) return null;
  return (
    <div className="mb-4 rounded-lg border border-border bg-secondary/40 px-4 py-3">
      <p className="text-sm font-semibold text-foreground">{info.tagline}</p>
      <p className="mt-0.5 text-sm text-muted-foreground">{info.description}</p>
    </div>
  );
}

// Read-only status strip — the old version also had the "Start incident" demo CI picker, removed
// now that real alerts (Diagnose / auto-triage) are the one real way to start a run. Only renders
// once something is actually happening, rather than taking up a permanent row for nothing.
function IncidentStatusBar({ incident }) {
  if (!incident.run && !incident.loading && !incident.error) return null;
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border bg-secondary/40 px-4 py-2 text-sm">
      {incident.loading && <span className="text-xs text-muted-foreground">Running…</span>}
      {incident.run && incident.run.status === "historical" && (
        <span className="text-xs text-muted-foreground">
          {incident.run.external_id} — historical ticket, not a live run
        </span>
      )}
      {incident.run && incident.run.status !== "historical" && (
        <span className="text-xs text-muted-foreground">
          {incident.run.incident_id} — {incident.run.status}
          {incident.run.verification_status ? ` (${incident.run.verification_status})` : ""} ·
          modality: {incident.run.modality}
        </span>
      )}
      {incident.error && <span className="text-xs text-red-500">{incident.error}</span>}
      <span className="ml-auto text-xs text-muted-foreground">
        Open Incident Workspace for the full record, including the Agent Trace.
      </span>
    </div>
  );
}

// Cockpit layout: sidebar + a shared "active incident" (golden path) + tabbed workspace. One
// workflow-run hook lives here and is passed to every tab that shows a run, so starting an
// incident on one tab is visible consistently on the others (as far as the no-checkpointing
// architecture allows — see IncidentWorkspace.jsx's ApprovalSection for the "approve re-runs, doesn't resume" limitation).
export default function CockpitShell({ token, onTokenChange, apiBase, username, onLogout }) {
  // The active role is decoded from the JWT itself — real POST /auth/login sets it from the
  // authenticated account's own role; POST /auth/view-as (admin-only, Sidebar) can temporarily
  // overlay a different role for demo/testing, carrying real_* claims so the UI can show an honest
  // "viewing as" banner rather than silently pretending the admin IS the other user.
  const identity = useMemo(() => {
    const payload = decodeJwtPayload(token) || {};
    return {
      username: payload.sub || null,
      role: payload.role || "ops_engineer",
      displayName: payload.display_name || null,
      realUsername: payload.real_username || null,
      realRole: payload.real_role || null,
      realDisplayName: payload.real_display_name || null,
    };
  }, [token]);

  const visibleTabs = useMemo(
    () => TABS.filter((tab) => (TAB_PERMISSIONS[identity.role] || []).includes(tab)),
    [identity.role]
  );

  const [activeTab, setActiveTab] = useState(visibleTabs[0]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  // Sidebar itself never renders below md (no room for a permanent side column on a phone) — this
  // instead opens it as a full-screen drawer, independent of the desktop collapsed/expanded state.
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { alerts, totalReceived, connectionStatus } = useAlertStream({ apiBase, token });
  const incident = useWorkflowRun({ apiBase, token });
  const { tickets, refetch: refetchTickets } = useTickets(apiBase, token);
  const { notifications } = useAutoTriage({ alerts, tickets, incident, refetchTickets });

  // If an admin's "view as" hides the currently-active tab, fall back to the first tab that role
  // can still see rather than rendering a tab the role no longer has permission for.
  useEffect(() => {
    if (!visibleTabs.includes(activeTab)) setActiveTab(visibleTabs[0]);
  }, [visibleTabs, activeTab]);

  // Shared by Ops Board's Ticket History / correlated-candidate status pills and the notification
  // bell — jump to Incident Workspace showing exactly that run, not just "the latest one".
  function openIncident(runOrTraceSnapshot) {
    incident.setRun(runOrTraceSnapshot);
    setActiveTab("Incident Workspace");
  }

  async function openTicket(ticket) {
    const res = await apiFetch(apiBase, `/tickets/${ticket.id}`, { token });
    if (!res.ok) return;
    const detail = await res.json();
    openIncident(detail.trace_snapshot);
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((v) => !v)}
        identity={identity}
        connectionStatus={connectionStatus}
        apiBase={apiBase}
        token={token}
        onTokenChange={onTokenChange}
        incident={incident}
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-header px-3 py-3 text-header-foreground sm:px-6">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              title="Open menu"
              className="-ml-1 shrink-0 rounded-md p-1.5 text-header-foreground/80 hover:bg-secondary hover:text-foreground md:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <LogoMark size={26} className="shrink-0" />
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold leading-tight">OpsFlow</h1>
              <p className="hidden truncate text-xs text-muted-foreground leading-tight sm:block">
                AI-verified operations console
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-sm text-header-foreground/80 sm:gap-3">
            {identity.realUsername ? (
              <span className="hidden rounded-md border border-accent/40 bg-accent-soft px-2 py-1 text-xs text-foreground sm:inline">
                {identity.realDisplayName} viewing as <span className="font-medium">{identity.displayName}</span> ({ROLE_LABELS[identity.role]})
              </span>
            ) : (
              <span className="hidden sm:inline">
                {identity.displayName || username}
                <span className="text-muted-foreground"> · {ROLE_LABELS[identity.role]}</span>
              </span>
            )}
            <NotificationBell notifications={notifications} onOpenNotification={(n) => openIncident(n.run)} />
            <Button variant="outline" size="sm" onClick={onLogout}>
              Log out
            </Button>
          </div>
        </header>

        <div className="relative shrink-0 border-b border-border bg-card">
          <nav className="flex gap-1 overflow-x-auto px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {visibleTabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                title={TAB_INFO[tab]?.description}
                className={cn(
                  "whitespace-nowrap border-b-2 border-transparent px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground",
                  activeTab === tab && "border-accent font-medium text-foreground"
                )}
              >
                {tab}
              </button>
            ))}
          </nav>
          {/* Hints that the tab bar scrolls — only matters on narrow screens where tabs actually
              overflow; the bar has no scrollbar of its own (hidden above) so without this a user has
              no visual cue that swiping reveals more tabs. */}
          <div className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-card to-transparent sm:hidden" />
        </div>

        <IncidentStatusBar incident={incident} />

        <main className="min-w-0 flex-1 overflow-y-auto p-6">
          <TabInfoBanner tab={activeTab} />
          {activeTab === "Overview" && <Overview apiBase={apiBase} token={token} />}
          {activeTab === "Ops Board" && (
            <OpsBoard
              apiBase={apiBase}
              token={token}
              alerts={alerts}
              totalReceived={totalReceived}
              connectionStatus={connectionStatus}
              incident={incident}
              tickets={tickets}
              refetchTickets={refetchTickets}
              onOpenTicket={openTicket}
            />
          )}
          {activeTab === "Tickets" && (
            <Tickets apiBase={apiBase} token={token} tickets={tickets} refetchTickets={refetchTickets} onOpenTicket={openTicket} />
          )}
          {activeTab === "Incident Workspace" && (
            <IncidentWorkspace incident={incident} apiBase={apiBase} token={token} identity={identity} />
          )}
          {activeTab === "Drift Queue" && <DriftQueue apiBase={apiBase} token={token} />}
          {activeTab === "Autonomy Ladder" && <AutonomyLadder apiBase={apiBase} token={token} />}
        </main>
      </div>

      <ChatWidget apiBase={apiBase} token={token} incident={incident} onOpenIncident={openIncident} onOpenTicket={openTicket} />
    </div>
  );
}
