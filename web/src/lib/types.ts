export type ClaimStatus = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "NEEDS_REVIEW" | "UNSUPPORTED";
export type ReviewStatus = "PROCESSING" | "IN_REVIEW" | "COMPLETE";
export type ReviewAction = "ACCEPT" | "OVERRIDE" | "ESCALATE";
export type OverrideReason =
  | "Label language is equivalent"
  | "Within fair balance"
  | "Supported by other section"
  | "Other";

export interface ReviewSummary {
  id: string;
  document_id: string;
  filename: string;
  drug_name: string | null;
  status: ReviewStatus;
  total_claims: number;
  reviewed_claims: number;
  created_at: string;
}

export interface ClaimDecision {
  action: string;
  override_reason: string | null;
  override_detail: string | null;
  decided_at: string | null;
}

export interface ClaimEvaluation {
  id: string;
  claim_id: string;
  claim_text: string;
  start_offset: number;
  end_offset: number;
  status: ClaimStatus;
  reasoning: string;
  citation_text: string | null;
  citation_section: string | null;
  citation_verified: boolean;
  decision: ClaimDecision | null;
}

export interface ReviewDetail {
  review_id: string;
  document_id: string;
  filename: string;
  drug_name: string | null;
  extracted_text: string | null;
  status: ReviewStatus;
  total_claims: number;
  reviewed_claims: number;
  evaluations: ClaimEvaluation[];
}

export interface ParseResult {
  document_id: string;
  filename: string;
  drug_name: string | null;
  extracted_text_length: number;
  claim_count: number;
  claims: Array<{
    id: string;
    text: string;
    start_offset: number;
    end_offset: number;
  }>;
}

export interface EvaluateResult {
  review_id: string;
  document_id: string;
  filename: string;
  drug_name: string | null;
  total_claims: number;
  supported: number;
  partially_supported: number;
  needs_review: number;
  unsupported: number;
  evaluations: ClaimEvaluation[];
}

export interface DecisionResult {
  decision_id: string;
  action: string;
  session_status: string;
}

export interface LabelDrug {
  drug_name: string;
  set_id: string;
  section_count: number;
  statement_count: number;
}

export interface LabelStatement {
  id: string;
  drug_name: string;
  set_id: string;
  section_name: string;
  statement_text: string;
  ingested_at: string;
}
