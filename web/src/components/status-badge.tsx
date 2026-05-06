import type { ClaimStatus, ReviewStatus } from "@/lib/types";

const CLAIM_STATUS_STYLES: Record<ClaimStatus, { bg: string; text: string; ring: string; label: string }> = {
  SUPPORTED: { bg: "bg-supported/10", text: "text-supported", ring: "ring-supported/20", label: "SUPPORTED" },
  PARTIALLY_SUPPORTED: { bg: "bg-partial/10", text: "text-partial", ring: "ring-partial/20", label: "PARTIAL" },
  NEEDS_REVIEW: { bg: "bg-review/10", text: "text-review", ring: "ring-review/20", label: "REVIEW" },
  UNSUPPORTED: { bg: "bg-unsupported/10", text: "text-unsupported", ring: "ring-unsupported/20", label: "UNSUP" },
};

const REVIEW_STATUS_STYLES: Record<ReviewStatus, { bg: string; text: string; ring: string; label: string }> = {
  PROCESSING: { bg: "bg-text-muted/10", text: "text-text-muted", ring: "ring-text-muted/20", label: "PROCESSING" },
  IN_REVIEW: { bg: "bg-partial/10", text: "text-partial", ring: "ring-partial/20", label: "IN REVIEW" },
  COMPLETE: { bg: "bg-supported/10", text: "text-supported", ring: "ring-supported/20", label: "COMPLETE" },
};

export function ClaimStatusBadge({ status }: { status: ClaimStatus }) {
  const style = CLAIM_STATUS_STYLES[status];
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${style.bg} ${style.text} ${style.ring}`}>
      {style.label}
    </span>
  );
}

export function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  const style = REVIEW_STATUS_STYLES[status];
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${style.bg} ${style.text} ${style.ring}`}>
      {style.label}
    </span>
  );
}
