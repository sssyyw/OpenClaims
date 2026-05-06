import type {
  ReviewSummary,
  ReviewDetail,
  ParseResult,
  EvaluateResult,
  DecisionResult,
  ReviewAction,
  OverrideReason,
  LabelDrug,
  LabelStatement,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export async function listReviews(): Promise<ReviewSummary[]> {
  const data = await fetchJSON<{ reviews: ReviewSummary[] }>("/api/reviews/");
  return data.reviews;
}

export async function getReview(reviewId: string): Promise<ReviewDetail> {
  return fetchJSON<ReviewDetail>(`/api/reviews/${reviewId}`);
}

export async function parseDocument(file: File, drugName?: string): Promise<ParseResult> {
  const form = new FormData();
  form.append("file", file);
  if (drugName) form.append("drug_name", drugName);
  return fetchJSON<ParseResult>("/api/claims/parse", { method: "POST", body: form });
}

export async function evaluateDocument(documentId: string): Promise<EvaluateResult> {
  return fetchJSON<EvaluateResult>(`/api/claims/evaluate/${documentId}`, { method: "POST" });
}

// --- Labels / Content Management ---

export async function listLabelDrugs(): Promise<LabelDrug[]> {
  const data = await fetchJSON<{ drugs: LabelDrug[] }>("/api/labels/drugs");
  return data.drugs;
}

export async function searchLabelDrugs(query: string): Promise<LabelDrug[]> {
  const data = await fetchJSON<{ results: LabelDrug[] }>(
    `/api/labels/drugs/search?q=${encodeURIComponent(query)}`,
  );
  return data.results;
}

export async function getDrugStatements(setId: string): Promise<LabelStatement[]> {
  const data = await fetchJSON<{ statements: LabelStatement[] }>(
    `/api/labels/drugs/${encodeURIComponent(setId)}/statements`,
  );
  return data.statements;
}

export async function ingestLabelFile(file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await fetchJSON<unknown>("/api/labels/ingest/file", { method: "POST", body: form });
}

// --- Reviews ---

export async function decideClaim(
  reviewId: string,
  evaluationId: string,
  action: ReviewAction,
  overrideReason?: OverrideReason,
  overrideDetail?: string,
): Promise<DecisionResult> {
  return fetchJSON<DecisionResult>(
    `/api/reviews/${reviewId}/claims/${evaluationId}/decide`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        override_reason: overrideReason || null,
        override_detail: overrideDetail || null,
      }),
    },
  );
}
