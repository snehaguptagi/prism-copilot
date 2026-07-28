// Indian-currency display helpers. Values come from the API in rupees.
// A book here spans ~₹38 lakh (a young trader) to ~₹13.5 crore (an ex-banker),
// so we render lakh vs crore adaptively instead of forcing everything to "Cr"
// (which would round a ₹38 lakh account down to a nonsensical "₹0 Cr").

const IN = "en-IN";

/** Full adaptive figure: crore at/above ₹1 Cr, lakh below. */
export function inr(value: number): string {
  const cr = value / 1e7;
  if (cr >= 100) return `₹${cr.toLocaleString(IN, { maximumFractionDigits: 0 })} Cr`;
  if (cr >= 1) return `₹${cr.toLocaleString(IN, { maximumFractionDigits: 2 })} Cr`;
  const lakh = value / 1e5;
  return `₹${lakh.toLocaleString(IN, { maximumFractionDigits: 1 })} L`;
}

/** Numeric crore value (one decimal) for NumberFlow-animated headline stats. */
export function crValue(value: number): number {
  return Math.round((value / 1e7) * 10) / 10;
}

/** Numeric lakh value for smaller headline stats (e.g. annual fee revenue). */
export function lakhValue(value: number): number {
  return Math.round(value / 1e5);
}
