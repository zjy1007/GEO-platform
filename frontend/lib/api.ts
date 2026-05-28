// Shared API client + type definitions for the GEO 商家画像平台 frontend.
// All endpoints live under the FastAPI backend base URL. No auth header needed
// in local dev (auth is disabled there).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

// ---------------------------------------------------------------------------
// Types (mirror the backend pydantic schemas)
// ---------------------------------------------------------------------------

export interface MerchantBase {
  name: string;
  category?: string | null;
  city?: string | null;
  district?: string | null;
  address?: string | null;
  phone?: string | null;
  website?: string | null;
  business_hours?: string | null;
  price_range?: string | null;
  services?: string[] | null;
  target_keywords?: string[] | null;
  official_sources?: string[] | null;
  competitors?: string[] | null;
}

export interface MerchantOut extends MerchantBase {
  id: string;
  tenant_id: string;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type MerchantCreate = MerchantBase;
export type MerchantUpdate = Partial<MerchantBase>;

export interface CompletenessResult {
  score: number;
  filled_fields: string[];
  missing_fields: string[];
  suggestions: string[];
}

export interface NapCheckResult {
  consistent: boolean;
  issues: string[];
}

export interface AliasOut {
  id: string;
  alias: string;
  alias_type?: string | null;
  confidence?: number | null;
}

export type PromptTier = "basic" | "standard" | "professional";

export interface PromptGenerateRequest {
  tier: PromptTier;
  count?: number | null;
  modes: string[];
  phases: string[];
  provider: string;
}

export interface GeoPromptOut {
  id: string;
  scenario_type?: string | null;
  phase?: string | null;
  mode?: string | null;
  prompt_text?: string | null;
  city?: string | null;
  category?: string | null;
  intent?: string | null;
  created_at?: string | null;
}

export interface PromptGenerateResponse {
  total: number;
  prompts: GeoPromptOut[];
}

export interface GeoRunCreate {
  merchant_id: string;
  run_type?: "organic_eval" | "diagnostic_eval";
  providers: string[];
  prompt_count?: number | null;
  repeat_count?: number;
  modes?: string[] | null;
  phases?: string[] | null;
}

export interface GeoRunOut {
  id: string;
  merchant_id: string;
  run_type?: string | null;
  status?: string | null;
  total_jobs?: number | null;
  finished_jobs?: number | null;
  failed_jobs?: number | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface GeoRunProgress {
  run_id: string;
  status?: string | null;
  total_jobs: number;
  finished_jobs: number;
  failed_jobs: number;
  progress: number;
}

export interface ProviderResultOut {
  id: string;
  prompt_id?: string | null;
  provider?: string | null;
  channel?: string | null;
  model?: string | null;
  answer_text?: string | null;
  latency_ms?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  status?: string | null;
  created_at?: string | null;
  prompt_text?: string | null;
  prompt_phase?: string | null;
  prompt_mode?: string | null;
}

export interface MentionResultOut {
  id: string;
  provider_result_id: string;
  merchant_id: string;
  is_mentioned?: boolean | null;
  mention_text?: string | null;
  rank_position?: number | null;
  mentioned_brands?: Array<Record<string, unknown>> | null;
  sentiment?: string | null;
  confidence?: number | null;
}

export interface ExtractResponse {
  enqueued: number;
}

export type SourceType =
  | "official_website"
  | "user_upload"
  | "map"
  | "review"
  | "news"
  | "social"
  | "other";

export interface EvidenceSourceIn {
  source_type?: SourceType;
  url?: string | null;
  title?: string | null;
  text?: string | null;
}

export interface EvidenceSourceOut {
  id: string;
  merchant_id: string;
  source_type?: string | null;
  url?: string | null;
  title?: string | null;
  content_text?: string | null;
  trust_level?: number | null;
  retrieved_at?: string | null;
  content_hash?: string | null;
}

export interface VerificationResultOut {
  id: string;
  provider_result_id: string;
  claim_text?: string | null;
  verification_status?: string | null;
  evidence_source_id?: string | null;
  confidence?: number | null;
  explanation?: string | null;
}

export interface GeoReportOut {
  id: string;
  run_id: string;
  merchant_id: string;
  geo_score?: number | null;
  mention_rate?: number | null;
  evidence_rate?: number | null;
  positive_rate?: number | null;
  rank_score?: number | null;
  report_json?: Record<string, unknown> | null;
  created_at?: string | null;
}

// Terminal geo-run statuses — once reached, polling can stop.
export const TERMINAL_RUN_STATUSES = ["completed", "partial_failed", "failed"];

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Thin wrapper around fetch that prefixes the API base, sets JSON headers,
 * and turns non-2xx responses / network failures into thrown errors with a
 * friendly Chinese message. Returns parsed JSON (or undefined for 204).
 */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch (e) {
    // Network-level failure (backend down, CORS, etc.)
    throw new ApiError(
      `无法连接后端：${e instanceof Error ? e.message : String(e)}`,
      0
    );
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
      else if (body && Array.isArray(body.detail))
        detail = body.detail.map((d: { msg?: string }) => d.msg).join("; ");
    } catch {
      // ignore parse error, keep generic detail
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

// ---------------------------------------------------------------------------
// Endpoint helpers
// ---------------------------------------------------------------------------

export const api = {
  listMerchants: (limit = 50, offset = 0) =>
    apiFetch<MerchantOut[]>(`/merchants?limit=${limit}&offset=${offset}`),
  createMerchant: (payload: MerchantCreate) =>
    apiFetch<MerchantOut>(`/merchants`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMerchant: (id: string) => apiFetch<MerchantOut>(`/merchants/${id}`),
  updateMerchant: (id: string, payload: MerchantUpdate) =>
    apiFetch<MerchantOut>(`/merchants/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  completeness: (id: string) =>
    apiFetch<CompletenessResult>(`/merchants/${id}/completeness`),
  napCheck: (id: string) =>
    apiFetch<NapCheckResult>(`/merchants/${id}/nap-check`),
  aliases: (id: string) => apiFetch<AliasOut[]>(`/merchants/${id}/aliases`),

  listPrompts: (id: string) =>
    apiFetch<GeoPromptOut[]>(`/merchants/${id}/prompts`),
  generatePrompts: (id: string, payload: PromptGenerateRequest) =>
    apiFetch<PromptGenerateResponse>(`/merchants/${id}/prompts`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createGeoRun: (payload: GeoRunCreate) =>
    apiFetch<GeoRunOut>(`/geo-runs`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getGeoRun: (runId: string) =>
    apiFetch<GeoRunProgress>(`/geo-runs/${runId}`),
  runResults: (runId: string) =>
    apiFetch<ProviderResultOut[]>(`/geo-runs/${runId}/results`),
  extractMentions: (runId: string) =>
    apiFetch<ExtractResponse>(`/geo-runs/${runId}/extract`, {
      method: "POST",
    }),
  runMentions: (runId: string) =>
    apiFetch<MentionResultOut[]>(`/geo-runs/${runId}/mentions`),

  generateReport: (runId: string) =>
    apiFetch<GeoReportOut>(`/reports/${runId}/generate`, { method: "POST" }),
  getReport: (runId: string) => apiFetch<GeoReportOut>(`/reports/${runId}`),
  reportHtmlUrl: (runId: string) => `${API_BASE}/reports/${runId}/html`,

  listEvidence: (merchantId: string) =>
    apiFetch<EvidenceSourceOut[]>(`/merchants/${merchantId}/evidence`),
  addEvidence: (merchantId: string, payload: EvidenceSourceIn) =>
    apiFetch<EvidenceSourceOut>(`/merchants/${merchantId}/evidence`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyRun: (runId: string) =>
    apiFetch<ExtractResponse>(`/geo-runs/${runId}/verify`, { method: "POST" }),
  runVerifications: (runId: string) =>
    apiFetch<VerificationResultOut[]>(`/geo-runs/${runId}/verifications`),
};
