/** PwC + PRISM product lockup. The mark is built from CSS so it stays crisp,
 * inherits theme contrast, and does not introduce a remote image dependency. */
export function PwcMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`pwc-mark${compact ? " pwc-mark-compact" : ""}`} aria-label="PwC">
      <span className="pwc-symbol" aria-hidden="true">
        <span className="pwc-bar pwc-bar-one" />
        <span className="pwc-bar pwc-bar-two" />
        <span className="pwc-bar pwc-bar-three" />
      </span>
      <span className="pwc-word">pwc</span>
    </span>
  );
}

export function Logo() {
  return (
    <span className="brand-lockup">
      <PwcMark compact />
      <span className="brand-divider" aria-hidden="true" />
      <span className="brand-product">
        <span className="brand-word">PRISM</span>
        <span className="brand-subtitle">Portfolio intelligence</span>
      </span>
    </span>
  );
}
