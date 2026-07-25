export type RiskTier = "Low" | "Moderate" | "Elevated" | "High" | "Very High";

export interface Portfolio {
  portfolio_id: string;
  name: string;
  mandate: string;
  manager_name: string | null;
  manager_bio: string | null;
  risk_driver: string;
  risk_tier: RiskTier | null;
  est_vol: number | null;
  num_holdings: number | null;
  largest_class: string | null;
  largest_class_pct: number | null;
}

export interface Citation {
  url: string;
  title: string;
  cited_text: string;
  linked_security_ids: string[];
}

export interface PortfolioImpact {
  portfolio_id: string;
  portfolio_name: string;
  risk_tier: string;
  pct_nav_touched: number;
  matched_holdings: { security_id: string; weight_pct: number }[];
  vs_reference_pct: number;
  vs_reference_multiple: number | string | null;
}

export interface FactorSignal {
  factor: string;
  direction: "up" | "down" | "mixed";
  snippet: string;
}

export interface FactorImpact {
  portfolio_id: string;
  portfolio_name: string;
  tailwind_pct: number;
  headwind_pct: number;
  matched: { security_id: string; factor: string; effect: "tailwind" | "headwind"; weight_pct: number }[];
}

export interface CrossDeskContradiction {
  factor: string;
  tailwind_fund: string;
  tailwind_pct: number;
  headwind_fund: string;
  headwind_pct: number;
}

export interface ScenarioImpact {
  portfolio_id: string;
  portfolio_name: string;
  bands: { mild: number; moderate: number; severe: number };
}

export interface Psychographics {
  decision_style: string;
  loss_aversion: string;
  financial_literacy: string;
  engagement: string;
  comms_pref: string;
  primary_goal: string;
  time_horizon: string;
  life_stage: string;
}

export interface Communication {
  date: string;
  channel: string;
  direction: "inbound" | "outbound" | "both";
  summary: string;
}

export interface NextAction {
  due: string;
  action: string;
  priority: "Low" | "Normal" | "High";
}

export interface Relationship {
  referral_source: string;
  dependents: string;
  satisfaction: string;
  manager_note: string;
}

export interface Client {
  name: string;
  age: number;
  occupation: string;
  persona: string;
  email: string;
  phone: string;
  city: string;
  relationship_since: string;
  aum_fee_pct: number;
  risk_mandate: string;
  psychographics?: Psychographics;
  relationship?: Relationship;
  communications?: Communication[];
  next_action?: NextAction;
}

export interface PortfolioInsights {
  num_holdings: number;
  num_sectors: number;
  est_vol: number | null;
  wtd_beta: number | null;
  top_position_name: string | null;
  top_position_pct: number;
  largest_sector: string | null;
  largest_sector_pct: number | null;
  concentration: string;
  factor_exposures: { factor: string; pct: number }[];
}

export interface ClientHolding {
  security_id: string;
  name: string;
  ticker: string;
  weight_pct: number;
  market_value: number;
}

export interface SectorWeight {
  sector: string;
  weight_pct: number;
}

export interface Overview {
  kpis: {
    total_aum: number;
    client_count: number;
    holdings_count: number;
    distinct_securities: number;
    blended_fee_pct: number;
    annual_fee_revenue: number;
  };
  risk_distribution: { tier: RiskTier; count: number; aum: number }[];
  asset_class_allocation: { asset_class: string; value: number; pct: number }[];
  sector_allocation: { sector: string; value: number; pct: number }[];
  top_holdings: {
    security_id: string;
    name: string;
    ticker: string;
    sector: string;
    value: number;
    pct_of_book: number;
    held_by_count: number;
  }[];
  largest_clients: {
    portfolio_id: string;
    client_name: string;
    portfolio_name: string;
    risk_tier: RiskTier | null;
    aum: number;
  }[];
}

export interface ClientAccount {
  portfolio_id: string;
  portfolio_name: string;
  mandate: string;
  risk_driver?: string;
  risk_tier: RiskTier | null;
  est_vol?: number | null;
  aum: number;
  client: Client;
  insights?: PortfolioInsights;
  holdings: ClientHolding[];
  sector_breakdown: SectorWeight[];
  suggested_sector: string | null;
}

export interface LensResult {
  sector: string;
  narrative: string;
  citations: Citation[];
  portfolio_impact: PortfolioImpact[];
  factor_signals: FactorSignal[];
  factor_impact: FactorImpact[];
  cross_desk_contradictions: CrossDeskContradiction[];
  scenario_impact: ScenarioImpact[];
  note: string;
}

export interface AffectedClient {
  portfolio_id: string;
  portfolio_name: string;
  client_name: string;
  how_affected: string;
  talking_point: string;
}

export interface NewsFeedResult {
  category: string;
  tldr: string;
  key_points: string[];
  key_stats: string[];
  affected_clients: AffectedClient[];
  narrative: string;
  citations: Citation[];
  note: string;
}

export interface ProductItem {
  security_id: string;
  name: string;
  ticker: string;
  sector: string;
  instrument_type: string;
  asset_class: string;
  vol: number | null;
  beta: number | null;
  credit_quality: string | null;
  held_by_count: number;
}

export interface Products {
  total: number;
  groups: { asset_class: string; count: number; items: ProductItem[] }[];
}

export interface TalkingPointsResult {
  portfolio_id: string;
  portfolio_name: string;
  client_name: string;
  sector: string;
  narrative_summary?: string;
  citations: Citation[];
  impact: PortfolioImpact | null;
  factor_impact: FactorImpact | null;
  points: string[];
  note: string;
}
