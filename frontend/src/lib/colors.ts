import { RiskTier } from "./types";

/**
 * Chart colour on PwC's palette, with one hard constraint discovered by measuring
 * rather than assuming: **PwC's brand colours cannot encode categories.**
 *
 * Validated against white, their supporting palette fails outright — Yellow
 * #FFB600 sits at 1.76:1 contrast and OKLCH L 0.823 (outside the usable band), and
 * Tangerine/Yellow are only ΔE 10.9 apart to NORMAL colour vision, under the hard
 * floor of 15. A palette built from Orange, Tangerine, Yellow and Rose is four
 * versions of the same signal. It is superb for being recognised and useless for
 * being told apart.
 *
 * So the split is: the warm spectrum stays in identity (logo, page backdrop), PwC
 * Orange doubles as the single UI accent, and charts use a validated set that
 * keeps orange in slot 1 and goes cool for the rest. Both modes PASS all five
 * computable checks:
 *
 *   light (on #FFFFFF): worst adjacent CVD ΔE 11.6, normal-vision floor 20.5
 *   dark  (on #1F1F1F): worst adjacent CVD ΔE  8.2, normal-vision floor 15.3
 *
 * Dark steps were validated against the dark surface directly, not lightened from
 * the light set.
 *
 * The structural rule from the previous pass still holds and is what keeps the
 * accent meaningful: any mark that already carries its own label takes the accent
 * instead of a hue of its own (see ACCENT_SERIES). Categorical hues are spent only
 * where a mark cannot be labelled in place — the allocation donut.
 */

export const SEVERITY_COLOR: Record<RiskTier, string> = {
  Low: "var(--sev-low)",
  Moderate: "var(--sev-moderate)",
  Elevated: "var(--sev-elevated)",
  High: "var(--sev-high)",
  "Very High": "var(--sev-vhigh)",
};

export const SEVERITY_SCORE: Record<RiskTier, number> = {
  Low: 15,
  Moderate: 35,
  Elevated: 55,
  High: 75,
  "Very High": 95,
};

export function severityColor(tier: string | null): string {
  return (tier && SEVERITY_COLOR[tier as RiskTier]) || "var(--text-faint)";
}

export function severityScore(tier: string | null): number {
  if (!tier) return 10;
  return SEVERITY_SCORE[tier as RiskTier] ?? 10;
}

/**
 * The single accent, for any series that is already identified by its own label.
 * Used by the sector-exposure bars, where 14 named rows previously consumed 14
 * hues to encode information the row label had already given — decoration
 * dressed as an encoding, and past the 8-hue ceiling a categorical palette can
 * actually keep distinguishable.
 */
export const ACCENT_SERIES = "var(--accent)";

// Avatar tints are identity, not data, so they may lean warm without the
// categorical constraints applying. They DO carry white initials, so every one is
// measured against white text: the three that came in under 4.5:1 as first drafted
// (#0E86A6 at 4.22, #5A9E4A at 3.27, #B5610A at 4.49) are darkened here rather
// than left to fail. Worst case in this set is now 4.80:1.
const AVATAR_PALETTE = [
  "#D04A02",
  "#0E6E8A",
  "#4A3AA7",
  "#A8326B",
  "#487F3B",
  "#6B4E9E",
  "#9E5409",
  "#8A4B1F",
];

export function initials(name: string): string {
  const parts = name.replace("&", " ").split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function avatarColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length];
}

/**
 * Sector bars are a labelled list, so they take the accent, not a hue each.
 * Kept as a function with the same signature as before so callers need no
 * change, and so a future genuinely-unlabelled sector chart has one place to
 * grow a real palette.
 */
export function sectorColor(sector: string): string {
  void sector; // identity comes from the row's own label, not from a hue
  return ACCENT_SERIES;
}

/**
 * Asset class IS categorical: the allocation donut cannot label a 4%-wide
 * segment in place, so identity has to come from hue plus the legend. Validated
 * order below; assigned in fixed order and never cycled.
 *
 * Cash is deliberately the neutral slot rather than a seventh hue. It is the
 * residual "not invested in anything" category, and the validator would reject a
 * grey as a chromatic slot anyway (below the chroma floor) — so it is declared a
 * neutral instead of being forced into a colour it cannot hold.
 */
const ASSET_CLASS_COLORS: Record<string, string> = {
  Equity: "var(--cat-1)",
  "Fixed Income": "var(--cat-2)",
  "Real Estate": "var(--cat-3)",
  Commodity: "var(--cat-4)",
  Hybrid: "var(--cat-5)",
  Alternatives: "var(--cat-6)",
  Cash: "var(--cat-neutral)",
};

export function assetClassColor(assetClass: string): string {
  return ASSET_CLASS_COLORS[assetClass] ?? "var(--cat-neutral)";
}
