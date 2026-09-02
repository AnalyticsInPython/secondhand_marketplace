/**
 * The crown mark, drawn as a vector so it scales and re-colours cleanly.
 *
 * This is a stylised Columbia crown motif, not the University's trademarked
 * lock-up. Swap in the official asset before anything ships publicly — Brian
 * has the Figma connection and can export it.
 */

export function CrownMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className ?? "h-6 w-6"} fill="currentColor">
      <path d="M4.2 24 L1.8 8 L9.4 13.6 L16 3.4 L22.6 13.6 L30.2 8 L27.8 24 Z" />
      <rect x="4.2" y="26" width="23.6" height="3.4" rx="1.7" />
    </svg>
  );
}

export function Logo({ inverse = false }: { inverse?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <CrownMark className={inverse ? "h-6 w-6 text-light" : "h-6 w-6 text-deep"} />
      <div className="leading-none">
        <div
          className={`text-[19px] font-bold tracking-[-0.02em] ${inverse ? "text-white" : "text-deep"}`}
        >
          Columbia Market
        </div>
        <div
          className={`mt-0.5 text-[7px] font-semibold tracking-[0.08em] ${
            inverse ? "text-light" : "text-ink2"
          }`}
        >
          VERIFIED @COLUMBIA.EDU
        </div>
      </div>
    </div>
  );
}
