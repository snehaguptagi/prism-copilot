/** PRISM logo — a prism refracting a single beam of light into a restrained
 * spectrum. The spectrum stays confined to the brand mark and never appears in
 * UI chrome, which is the same one-accent discipline the rest of the system
 * follows.
 *
 * On PwC's palette the concept lands almost too neatly: their brand device IS a
 * warm spectrum, so the refracted fan is Orange, Tangerine, Yellow and Rose in
 * order. This is the one place those four are allowed — identity, where being
 * recognised is the job. They are never used to encode data, because Yellow and
 * Tangerine are indistinguishable as marks (see globals.css). */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <linearGradient id="prism-face" x1="8" y1="6" x2="24" y2="27" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--brand-orange)" />
          <stop offset="1" stopColor="var(--ink)" />
        </linearGradient>
      </defs>
      {/* incoming beam — inherits the surrounding ink, so it reads on both themes */}
      <path d="M2 15.5 H12" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.6" strokeLinecap="round" />
      {/* prism triangle */}
      <path
        d="M16 4.5 L27 25.5 H5 Z"
        fill="url(#prism-face)"
        stroke="var(--ink)"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      {/* refracted fan — PwC's warm spectrum, in brand order */}
      <path d="M19.5 16 L30 12.5" stroke="var(--brand-yellow)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 17.6 L30 16" stroke="var(--brand-tangerine)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 19.2 L30 19.6" stroke="var(--brand-orange)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M19.8 20.8 L29.5 23" stroke="var(--brand-rose)" strokeWidth="1.5" strokeLinecap="round" />
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
