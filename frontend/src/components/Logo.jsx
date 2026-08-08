// Verascope's mark: a scope/reticle — two concentric rings and a center dot, the instrument that
// brings a true signal into focus out of noise. That's literally the product's job (500 raw alerts
// -> one verified root cause; "alert cleared" -> a fix confirmed to actually hold), so the mark
// isn't decoration, it's the thesis. Gradient runs signal-teal -> a cooler blue for depth.
export function LogoMark({ size = 28, className }) {
  const id = "verascope-logo-gradient";
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#14B8AA" />
          <stop offset="1" stopColor="#0E6BA8" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="13.5" stroke={`url(#${id})`} strokeWidth="2.2" />
      <circle cx="16" cy="16" r="7.5" stroke={`url(#${id})`} strokeWidth="2.2" />
      <circle cx="16" cy="16" r="2" fill={`url(#${id})`} />
    </svg>
  );
}

export function Wordmark({ markSize = 22, textClassName = "text-base font-semibold tracking-tight", className }) {
  return (
    <div className={`flex items-center gap-2 ${className || ""}`}>
      <LogoMark size={markSize} />
      <span className={textClassName}>Verascope</span>
    </div>
  );
}
