import { ClientAccount, GraphStatus, GraphSuggestionsResult, GraphViewResult, LensResult, NewsFeedResult, Overview, Portfolio, Products, TalkingPointsResult } from "./types";

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
