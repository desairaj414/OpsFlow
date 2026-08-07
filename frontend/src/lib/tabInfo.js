// Plain-language framing for each cockpit tab, written for a jury/business audience rather than
// an operator who already knows the architecture — every tab in the PRD's §7 list gets one here.
export const TAB_INFO = {
  "Ops Board": {
    tagline: "Where problems arrive",
    description:
      "The live queue of incoming alerts across the Microsoft 365 estate (SharePoint, OneDrive, Power Platform, Teams, Exchange, Dataverse). An operator sees a problem here first, or reports one directly by voice or a screenshot.",
  },
  "Incident Workspace": {
    tagline: "One incident, start to finish",
    description:
      "The single end-to-end view of one incident: what was reported, what evidence the system gathered, what the AI diagnosed, and what it's proposing to do — all before anything actually runs.",
  },
  "Agent Trace": {
    tagline: "How the AI got its answer",
    description:
      "A transparency panel over every AI hand-off in this incident — which model ran, how confident it was, and what it actually concluded — so a claim can be checked, not just trusted.",
  },
  "Approval Queue": {
    tagline: "The human checkpoint",
    description:
      "Where a person reviews and approves or rejects an AI-proposed action before it executes. This is the control point that keeps a human in the loop for anything above the system's current autonomy threshold.",
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
  "Chunk Inspector": {
    tagline: "Proof the AI isn't making things up",
    description:
      "A look under the hood at how runbook documents were split into retrievable pieces for the AI to cite from, so its recommendations are grounded in real documentation rather than invented.",
  },
  "Metrics & Eval": {
    tagline: "Is the system actually working",
    description:
      "The health of the system itself: how often incidents were genuinely resolved versus just had their symptoms masked, how well answers cite real evidence, and other trust metrics across every run so far.",
  },
};
