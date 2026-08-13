"use client";

import { useEffect, useState } from "react";
import { Radio, Settings, PlayCircle, ScrollText, Users, BookOpen, PanelLeftClose, PanelLeftOpen, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import { ROLE_LABELS, canSeePanel } from "@/lib/roles";
import { useTheme } from "@/hooks/useTheme";
import ScenarioLauncherPanel from "@/components/panels/ScenarioLauncherPanel.jsx";
import AuditLogPanel from "@/components/panels/AuditLogPanel.jsx";
import ModelThresholdConfigPanel from "@/components/panels/ModelThresholdConfigPanel.jsx";
import UserManagementPanel from "@/components/panels/UserManagementPanel.jsx";
import KnowledgeBasePanel from "@/components/ChunkInspector.jsx";
import { apiFetch } from "@/lib/api.js";

const NAV_ITEMS = [
  { key: "users", label: "User Management", icon: Users, Panel: UserManagementPanel },
  { key: "config", label: "Model & Threshold Config", icon: Settings, Panel: ModelThresholdConfigPanel },
  { key: "scenarios", label: "Scenario Launcher", icon: PlayCircle, Panel: ScenarioLauncherPanel },
  { key: "audit", label: "Audit Log", icon: ScrollText, Panel: AuditLogPanel },
  // Reference/admin content (browse chunks, upload runbooks/articles) — not needed on every
  // screen the way Ops Board/Incident Workspace are, so it lives here now instead of a main tab.
  { key: "knowledge", label: "Knowledge Base", icon: BookOpen, Panel: KnowledgeBasePanel },
];

// Push-to-talk used to live here (PRD §7's original voice modality). Moved into the floating
// ChatWidget's mic button by explicit request — one conversational surface instead of two, and it
// gets the assistant's fuller natural-language handling (not just the closed-vocabulary intent
// parser) for free. See ChatWidget.jsx and decisions-log.md's newest entry.

// Admin-only "View as" — scoped impersonation for demo/testing, NOT a self-service role picker
// (real auth: your role is fixed to your account from POST /auth/login; only an already-
// authenticated Admin can borrow another role, via the equally real POST /auth/view-as, which
// signs a new token that still honestly carries who's really logged in via real_* claims).
function ViewAsControl({ apiBase, token, onTokenChange, identity }) {
  const [users, setUsers] = useState([]);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState("");

  const isViewingAs = Boolean(identity.realUsername);
  const canUseViewAs = identity.role === "admin" || isViewingAs;

  useEffect(() => {
    if (!canUseViewAs || isViewingAs) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(apiBase, "/users", { token });
        if (res.ok && !cancelled) setUsers(await res.json());
      } catch {
        // Convenience picker, not load-bearing — silently leave it empty on failure.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, token, canUseViewAs, isViewingAs]);

  async function viewAs(userId) {
    if (!userId) return;
    setSwitching(true);
    setError("");
    try {
      const res = await apiFetch(apiBase, "/auth/view-as", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token,
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      onTokenChange((await res.json()).access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setSwitching(false);
    }
  }

  async function stopViewingAs() {
    setSwitching(true);
    setError("");
    try {
      const res = await apiFetch(apiBase, "/auth/stop-view-as", {
        method: "POST",
        token,
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      onTokenChange((await res.json()).access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setSwitching(false);
    }
  }

  if (!canUseViewAs) return null;

  if (isViewingAs) {
    return (
      <div className="rounded-md border border-accent/40 bg-accent-soft p-3">
        <p className="text-xs text-foreground">
          Viewing as <span className="font-medium">{identity.displayName}</span> ({ROLE_LABELS[identity.role]})
        </p>
        <Button size="sm" variant="outline" className="mt-2 w-full" onClick={stopViewingAs} disabled={switching}>
          Return to {identity.realDisplayName}
        </Button>
        {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted-foreground">View as (admin only)</label>
      <select
        className="w-full rounded-md border border-border bg-background px-2 py-2 text-sm focus:border-accent focus:outline-none"
        value=""
        onChange={(e) => viewAs(e.target.value)}
        disabled={switching}
      >
        <option value="">Choose a user to preview their view…</option>
        {users
          .filter((u) => u.username !== identity.username)
          .map((u) => (
            <option key={u.id} value={u.id}>
              {u.display_name} — {ROLE_LABELS[u.role] || u.role}
            </option>
          ))}
      </select>
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

// Sidebar shell: admin-only view-as control and role-gated admin panels.
// Collapsed by default (icon rail) — expand via the toggle button. Nav items open their panel in a
// Modal (works identically collapsed or expanded) rather than the old inline expansion, which got
// cramped inside a 256px-wide sidebar.
export default function Sidebar({ collapsed, onToggleCollapsed, identity, connectionStatus, apiBase, token, onTokenChange, incident }) {
  const { theme, toggleTheme } = useTheme();
  const [activePanel, setActivePanel] = useState(null);
  const visibleNavItems = NAV_ITEMS.filter((item) => canSeePanel(identity.role, item.key));
  const activeItem = visibleNavItems.find((n) => n.key === activePanel);
  const ActivePanelComponent = activeItem?.Panel;

  const navButtons = (iconOnly) =>
    visibleNavItems.map(({ key, label, icon: Icon }) => (
      <button
        key={key}
        onClick={() => setActivePanel(key)}
        title={label}
        className={cn(
          iconOnly
            ? "rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground"
            : "flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
        )}
      >
        <Icon className={iconOnly ? "h-5 w-5" : "h-4 w-4"} />
        {!iconOnly && label}
      </button>
    ));

  const modal = ActivePanelComponent && (
    <Modal
      open={Boolean(activePanel)}
      onClose={() => setActivePanel(null)}
      title={activeItem.label}
      className={activePanel === "knowledge" ? "max-w-3xl" : undefined}
    >
      <ActivePanelComponent apiBase={apiBase} token={token} incident={incident} identity={identity} />
    </Modal>
  );

  if (collapsed) {
    return (
      <>
        <aside className="flex w-14 shrink-0 flex-col items-center gap-3 border-r border-border bg-card py-4">
          <button
            onClick={onToggleCollapsed}
            title="Expand sidebar"
            className="rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <PanelLeftOpen className="h-5 w-5" />
          </button>
          <Radio className={cn("h-4 w-4", connectionStatus === "live" ? "text-green-600" : "text-red-500")} />
          {navButtons(true)}
          <button
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            className="mt-auto rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </aside>
        {modal}
      </>
    );
  }

  return (
    <>
      <aside className="flex w-64 shrink-0 flex-col gap-6 overflow-y-auto border-r border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Console</span>
          <div className="flex items-center gap-1">
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              onClick={onToggleCollapsed}
              title="Collapse sidebar"
              className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          </div>
        </div>

        <ViewAsControl apiBase={apiBase} token={token} onTokenChange={onTokenChange} identity={identity} />

        <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/50 p-3">
          <Radio className={cn("h-4 w-4", connectionStatus === "live" ? "text-green-600" : "text-red-500")} />
          <span className="text-xs text-muted-foreground">
            Live feed: {connectionStatus === "live" ? "connected" : connectionStatus}
          </span>
        </div>

        <nav className="flex flex-col gap-1">
          {navButtons(false)}
          {visibleNavItems.length === 0 && (
            <p className="px-3 py-2 text-xs text-muted-foreground">No admin panels available for this role.</p>
          )}
        </nav>
      </aside>
      {modal}
    </>
  );
}
