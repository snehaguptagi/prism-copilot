import { ClientAccount, GraphStatus, GraphSuggestionsResult, GraphViewResult, LensResult, NewsFeedResult, Overview, OverviewGraphResult, Portfolio, Products, TalkingPointsResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function errorMessage(res: Response, path: string): Promise<string> {
  try {
    const payload = (await res.json()) as { detail?: string };
    if (payload.detail) return payload.detail;
  } catch {
    // Fall back to the status label below when the response is not JSON.
  }
  return `${path} failed (${res.status} ${res.statusText})`;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await errorMessage(res, path));
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
    throw new Error(await errorMessage(res, path));
  }
  return res.json();
}

async function deleteJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await errorMessage(res, path));
  }
  return res.json();
}

export interface ManagerProfile {
  manager_name: string;
  role: string;
  firm: string;
}

export function getMe(): Promise<ManagerProfile> {
  return getJSON<ManagerProfile>("/me");
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
}

export interface AddClientResult {
  portfolio_id: string;
  client_name: string;
  risk_tier: string;
}

export function addClient(req: AddClientRequest): Promise<AddClientResult> {
  return postJSON<AddClientResult>("/clients", req);
}

export interface DeleteClientResult {
  portfolio_id: string;
  client_name: string;
  removed_holdings: number;
}

export function deleteClient(portfolioId: string): Promise<DeleteClientResult> {
  return deleteJSON<DeleteClientResult>(`/clients/${encodeURIComponent(portfolioId)}`);
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
