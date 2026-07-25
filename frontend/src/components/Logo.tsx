/** PRISM logo — a prism refracting a single beam of white light into a
 * restrained spectrum. Spectrum is used ONLY in the brand mark (identity),
 * never in the UI chrome, keeping faith with the one-accent design ethos. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <linearGradient id="prism-face" x1="8" y1="6" x2="24" y2="27" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7b74f2" />
          <stop offset="1" stopColor="#4a42db" />
        </linearGradient>
      </defs>
      {/* incoming white beam */}
      <path d="M2 15.5 H12" stroke="#c9cdda" strokeWidth="1.6" strokeLinecap="round" />
      {/* prism triangle */}
      <path
        d="M16 4.5 L27 25.5 H5 Z"
        fill="url(#prism-face)"
        stroke="#4a42db"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      {/* refracted spectrum fan */}
      <path d="M19.5 16 L30 12.5" stroke="#4cc4c0" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 17.6 L30 16" stroke="#5b53ed" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 19.2 L30 19.6" stroke="#c07dcf" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M19.8 20.8 L29.5 23" stroke="#e08a4d" strokeWidth="1.5" strokeLinecap="round" />
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
