import { RiskTier } from "./types";

/**
 * Chart colour, following the Perplexity deck's central argument: restraint.
 *
 * The deck's own bar chart paints every bar the same turquoise and relies on the
 * row label for identity. That is the right default and it is applied here
 * wherever a mark is already directly labelled (see ACCENT_SERIES). Categorical
 * hues are spent only where a mark genuinely cannot be labelled in place — the
 * allocation donut.
 *
 * Every categorical value below is the output of the data-viz validator, not a
 * hand-picked hex. Both sets PASS all five computable checks — lightness band,
 * chroma floor, protan/deutan adjacent separation, normal-vision floor, and
 * contrast against their own surface:
 *
 *   light (on #FCFCF9): worst adjacent CVD ΔE 11.6, normal-vision floor 20.7
 *   dark  (on #13343B): worst adjacent CVD ΔE  9.3, normal-vision floor 16.3
 *
 * For comparison the previous palette's worst adjacent pair was ΔE 8.6, so this
 * is a measurable improvement rather than a lateral restyle. Dark steps were
 * validated against the dark surface directly; they are not a lightened flip of
 * the light set.
 *
 * A note on the accent: Perplexity's turquoise #20808D FAILS the categorical
 * chroma floor (OKLCH C = 0.086, floor 0.10) — at that saturation it reads as
 * grey once it has to be told apart from other hues. It is therefore used
 * verbatim as the single accent, where there is nothing to distinguish it from,
 * while the categorical slot uses #008C9E: the same cyan-teal hue pushed over
 * the floor. Same family, measurably distinguishable.
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

const AVATAR_PALETTE = [
  "#20808D",
  "#4A3AA7",
  "#A8326B",
  "#B0710A",
  "#2F7A3D",
  "#6B4E9E",
  "#1C6B78",
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
