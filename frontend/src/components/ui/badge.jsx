import { cn } from "@/lib/utils";

// Three-badge system (PRD §7, rules-frontend.md honesty rule): nothing AI-generated may share the
// visual register of verified fact. Exactly three variants, deliberately distinct colors —
// "ai-proposed" (unverified model output), "human-approved" (a person signed off), "system-verified"
// (deterministic check, not a model guess and not a human either).
const VARIANTS = {
  "ai-proposed": "bg-violet-600/10 text-violet-700 border-violet-600/30 dark:text-violet-300",
  "human-approved": "bg-green-600/10 text-green-700 border-green-600/30 dark:text-green-300",
  "human-rejected": "bg-red-600/10 text-red-700 border-red-600/30 dark:text-red-300",
  "system-verified": "bg-blue-600/10 text-blue-700 border-blue-600/30 dark:text-blue-300",
};

const LABELS = {
  "ai-proposed": "AI-proposed",
  "human-approved": "Human-approved",
  "human-rejected": "Human-rejected",
  "system-verified": "System-verified",
};

export function Badge({ variant, className }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        VARIANTS[variant],
        className
      )}
    >
      {LABELS[variant]}
    </span>
  );
}
