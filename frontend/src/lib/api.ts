import { ClientAccount, GraphStatus, GraphSuggestionsResult, GraphViewResult, LensResult, NewsFeedResult, Overview, OverviewGraphResult, Portfolio, ProductSuggestion, Products, ProfileOptions, Psychographics, Security, TalkingPointsResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

async function sendJSON<T>(method: "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    // FastAPI puts the human-readable reason in `detail`; surface that rather
    // than a bare status code, since these are validation errors an RM can fix.
    let detail = `${res.status}`;
    try {
      const parsed = await res.json();
      detail = typeof parsed?.detail === "string" ? parsed.detail : JSON.stringify(parsed);
    } catch {
      detail = (await res.text()) || detail;
    }
    throw new Error(detail);
  }
  return res.json();
}

export function getMe(): Promise<{ manager_name: string }> {
  return getJSON<{ manager_name: string }>("/me");
}

export function getSectors(): Promise<string[]> {
  return getJSON<string[]>("/sectors");
}

export function getPortfolios(): Promise<Portfolio[]> {
  return getJSON<Portfolio[]>("/portfolios");
}

export function getClients(): Promise<ClientAccount[]> {
  return getJSON<ClientAccount[]>("/clients");
}

export interface AddClientRequest {
  name: string;
  occupation: string;
  city: string;
  risk_mandate: string;
  initial_aum: number;
  template_portfolio_id: string;
  age?: number;
  email?: string;
  phone?: string;
  persona?: string;
  psychographics?: Psychographics;
}

export interface AddClientResult {
  portfolio_id: string;
  client_name: string;
  risk_tier: string;
  has_profile: boolean;
}

export function addClient(req: AddClientRequest): Promise<AddClientResult> {
  return postJSON<AddClientResult>("/clients", req);
}

export function deleteClient(portfolioId: string): Promise<{ deleted: boolean }> {
  return sendJSON<{ deleted: boolean }>("DELETE", `/clients/${portfolioId}`);
}

export function getProfileOptions(): Promise<ProfileOptions> {
  return getJSON<ProfileOptions>("/profile-options");
}

export function getSecurities(): Promise<Security[]> {
  return getJSON<Security[]>("/securities");
}

export interface UpdateProfileResult {
  portfolio_id: string;
  psychographics: Psychographics;
  persona: string;
  product_suggestions: ProductSuggestion[];
}

export function updateProfile(
  portfolioId: string,
  body: { persona?: string; psychographics?: Psychographics },
): Promise<UpdateProfileResult> {
  return sendJSON<UpdateProfileResult>("PUT", `/clients/${portfolioId}/profile`, body);
}

export interface UpdateHoldingsResult {
  portfolio_id: string;
  num_holdings: number;
  aum: number;
  risk_tier: string;
  est_vol: number;
}

/** Weights are raw and need not total 100; the backend normalizes them. */
export function updateHoldings(
  portfolioId: string,
  holdings: { security_id: string; weight: number }[],
  nav?: number,
): Promise<UpdateHoldingsResult> {
  return sendJSON<UpdateHoldingsResult>("PUT", `/clients/${portfolioId}/holdings`, { holdings, nav });
}

export function getOverview(): Promise<Overview> {
  return getJSON<Overview>("/overview");
}

export function getProducts(): Promise<Products> {
  return getJSON<Products>("/products");
}

export function runLens(sector: string): Promise<LensResult> {
  return postJSON<LensResult>("/lens/run", { sector });
}

export function getNewsCategories(): Promise<string[]> {
  return getJSON<string[]>("/news/categories");
}

export function getNewsFeed(category: string, force = false): Promise<NewsFeedResult> {
  const q = `category=${encodeURIComponent(category)}${force ? "&force=true" : ""}`;
  return getJSON<NewsFeedResult>(`/news/feed?${q}`);
}

export function getTalkingPoints(portfolioId: string, sector: string): Promise<TalkingPointsResult> {
  return postJSON<TalkingPointsResult>("/talking-points", { portfolio_id: portfolioId, sector });
}

export function getGraphStatus(): Promise<GraphStatus> {
  return getJSON<GraphStatus>("/graph/status");
}

export function getGraphSuggestions(portfolioId: string): Promise<GraphSuggestionsResult> {
  return getJSON<GraphSuggestionsResult>(`/clients/${portfolioId}/graph-suggestions`);
}

export function getClientGraphView(portfolioId: string): Promise<GraphViewResult> {
  return getJSON<GraphViewResult>(`/clients/${portfolioId}/graph-view`);
}

export function getOverviewGraphView(): Promise<OverviewGraphResult> {
  return getJSON<OverviewGraphResult>("/graph/overview");
}
