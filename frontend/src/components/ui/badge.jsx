import { cn } from "@/lib/utils";

// Three-badge system (PRD §7, rules-frontend.md honesty rule): nothing AI-generated may share the
// visual register of verified fact. Exactly three variants, deliberately distinct colors, drawn
// from the brand's reserved status tokens (globals.css) rather than raw Tailwind palette utilities
// — "system-verified" deliberately uses the brand's signal teal (the same hue as the logo and
// primary actions), so "the system vouches for this" reads as one consistent meaning app-wide.
const VARIANTS = {
  "ai-proposed": "bg-status-ai/10 text-status-ai border-status-ai/30",
  "human-approved": "bg-status-good/10 text-status-good border-status-good/30",
  "human-rejected": "bg-status-critical/10 text-status-critical border-status-critical/30",
  "system-verified": "bg-accent-soft text-primary border-primary/30",
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
