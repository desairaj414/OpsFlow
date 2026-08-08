// UI-facing role vocabulary and permission matrix. Mirrors backend/main.py's ROLES/ROLE_TO_ACTOR_ROLE
// — this is display/gating only, the actual enforcement lives server-side (require_role() in
// main.py); a role hidden here but somehow still requested would be rejected with a 403, not
// silently allowed. Keep in sync by hand if the backend's role set changes.
export const ROLE_LABELS = {
  ops_engineer: "Ops Engineer",
  approver: "Approver",
  admin: "Admin",
};

// Which tabs each role sees. Overview is first for every role — the landing page after sign-in is
// now a real dashboard, not a raw alert feed (Ops Board moved to 2nd). All 3 roles see the same
// tab set; Admin's extra surface is the Sidebar panels, not additional main tabs. There is no
// separate Approval Queue tab — its decision UI lives inside Incident Workspace itself (rendered
// only when the shared run's status is pending_approval), gated by role there (`canDecide`): Ops
// Engineer can see a pending approval but not decide it, Approver/Admin can.
// Agent Trace is no longer a tab either — "View full Agent Trace" in Incident Workspace opens
// the same component in a Modal instead, since it only ever makes sense in the context of one
// incident (the tab always just read the same shared `run` Incident Workspace already shows).
export const TAB_PERMISSIONS = {
  ops_engineer: ["Overview", "Ops Board", "Tickets", "Incident Workspace", "Drift Queue", "Autonomy Ladder"],
  approver: ["Overview", "Ops Board", "Tickets", "Incident Workspace", "Drift Queue", "Autonomy Ladder"],
  admin: ["Overview", "Ops Board", "Tickets", "Incident Workspace", "Drift Queue", "Autonomy Ladder"],
};

// Which Sidebar panel(s) each role sees. Knowledge Base moved here from a main tab — it's
// reference/admin content (upload runbooks/articles, browse chunks), not something needed on
// every screen the way Ops Board/Incident Workspace are.
export const PANEL_PERMISSIONS = {
  ops_engineer: ["scenarios", "knowledge"],
  approver: ["scenarios", "audit", "knowledge"],
  admin: ["users", "config", "scenarios", "audit", "knowledge"],
};

export function canSeeTab(role, tab) {
  return (TAB_PERMISSIONS[role] || []).includes(tab);
}

export function canSeePanel(role, panelKey) {
  return (PANEL_PERMISSIONS[role] || []).includes(panelKey);
}
