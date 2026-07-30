/** PRISM logo — a prism refracting a single beam of light into a restrained
 * spectrum. The spectrum stays confined to the brand mark and never appears in
 * UI chrome, which is the same one-accent discipline the rest of the system
 * follows.
 *
 * Retuned to the peacock/turquoise world: the prism face is the accent, and the
 * fan is drawn from the four validated categorical steps rather than arbitrary
 * hues, so the mark is harmonious with the charts instead of a fifth palette. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <linearGradient id="prism-face" x1="8" y1="6" x2="24" y2="27" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2f97a4" />
          <stop offset="1" stopColor="#13343b" />
        </linearGradient>
      </defs>
      {/* incoming beam — peacock at low opacity, so it reads on paper and on ink */}
      <path d="M2 15.5 H12" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.6" strokeLinecap="round" />
      {/* prism triangle */}
      <path
        d="M16 4.5 L27 25.5 H5 Z"
        fill="url(#prism-face)"
        stroke="#13343b"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      {/* refracted fan — the validated categorical steps, in assignment order */}
      <path d="M19.5 16 L30 12.5" stroke="var(--cat-1)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 17.6 L30 16" stroke="var(--cat-3)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 19.2 L30 19.6" stroke="var(--cat-4)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M19.8 20.8 L29.5 23" stroke="var(--cat-2)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ size = 26 }: { size?: number }) {
  return (
    <span className="brand">
      <LogoMark size={size} />
      <span className="brand-word">PRISM</span>
    </span>
  );
}
