import { RiskTier } from "./types";

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

const AVATAR_PALETTE = [
  "#5850ec",
  "#0f766e",
  "#b45309",
  "#a3327d",
  "#4338ca",
  "#b45f2e",
  "#3f7d3f",
  "#7c3aed",
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

const SECTOR_COLORS: Record<string, string> = {
  Financials: "#5850ec",
  "Information Technology": "#0f9d9d",
  Energy: "#d97430",
  Commodity: "#b5850a",
  Gold: "#b57f00",
  Commodities: "#d46b2c",
  "Mutual Funds": "#7a4f9a",
  "Consumer Staples": "#3f7d3f",
  "Consumer Discretionary": "#c0567d",
  Industrials: "#6b7280",
  Materials: "#8b6f47",
  "Health Care": "#0e7490",
  "Communication Services": "#7c3aed",
  "Real Estate": "#a3327d",
  Utilities: "#4a6fa5",
  "Fixed Income": "#64748b",
  Cash: "#94a3b8",
};

export function sectorColor(sector: string): string {
  return SECTOR_COLORS[sector] ?? "#94a3b8";
}

const ASSET_CLASS_COLORS: Record<string, string> = {
  Equity: "#5850ec",
  "Fixed Income": "#0d9488", // validated: passes chroma floor + CVD separation on white
  "Real Estate": "#a3327d",
  Commodity: "#b5850a",
  Cash: "#64748b",
  Alternatives: "#7c3aed",
  Hybrid: "#2f7a3d", // validated against the rest of this palette on light + dark surfaces
};

export function assetClassColor(assetClass: string): string {
  return ASSET_CLASS_COLORS[assetClass] ?? "#94a3b8";
}
