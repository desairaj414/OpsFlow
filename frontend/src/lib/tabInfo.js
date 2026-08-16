// Plain-language framing for each cockpit tab, written for a jury/business audience rather than
// an operator who already knows the architecture — every tab in the PRD's §7 list gets one here.
export const TAB_INFO = {
  Overview: {
    tagline: "The headline view",
    description:
      "Session-wide health at a glance: how many incidents ran, how many the system verified were actually fixed, how much noise correlation cut through, and where the configuration records have drifted from the truth.",
  },
  "Ops Board": {
    tagline: "Where problems arrive",
    description:
      "The live queue of incoming alerts across the SaaS & automation estate (SharePoint, OneDrive, Power Platform, Teams, Exchange, Dataverse). An operator sees a problem here first, or reports one directly by voice or a screenshot. Alerts that arrive while you're connected diagnose themselves automatically, one at a time; the backlog already here when you opened this tab does not — run those with Diagnose or \"Run all untriaged\".",
  },
  Tickets: {
    tagline: "The ServiceNow / Jira system of record",
    description:
      "Every ticket this session's diagnoses have raised — in ServiceNow, since that's the one system alerts are ticketed in — browsed the way you'd browse a real ITSM instance. No live instance is connected in this build — \"Pull latest\" honestly re-reads local records instead of reaching out anywhere, and shows when it last did.",
  },
  "Incident Workspace": {
    tagline: "One incident, start to finish",
    description:
      "The single end-to-end view of one incident: what was reported, what evidence the system gathered, what the AI diagnosed, and what it's proposing to do. If it needs a human decision before running, that approve/reject step lives right here too.",
  },
  "Drift Queue": {
    tagline: "Is our records system telling the truth?",
    description:
      "Compares what the configuration database (CMDB) has on file against verified ground truth, surfacing where recorded service data has silently drifted from reality — a real, common IT problem.",
  },
  "Autonomy Ladder": {
    tagline: "How much trust has the AI earned",
    description:
      "Shows how much independent authority the AI currently holds per action type and environment — from 'always ask a human' up to 'auto-execute' — so nothing runs beyond what has been explicitly authorized.",
  },
};
