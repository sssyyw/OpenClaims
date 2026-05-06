"use client";

import type { ClaimEvaluation, ClaimStatus } from "@/lib/types";

const UNDERLINE_COLORS: Record<ClaimStatus, string> = {
  SUPPORTED: "var(--status-supported)",
  PARTIALLY_SUPPORTED: "var(--status-partial)",
  NEEDS_REVIEW: "var(--status-review)",
  UNSUPPORTED: "var(--status-unsupported)",
};

interface DocumentViewerProps {
  text: string;
  evaluations: ClaimEvaluation[];
  selectedClaimId: string | null;
  onSelectClaim: (id: string) => void;
}

export interface TextSegment {
  text: string;
  evaluation: ClaimEvaluation | null;
}

export function buildSegments(text: string, evaluations: ClaimEvaluation[]): TextSegment[] {
  const sorted = [...evaluations].sort((a, b) => a.start_offset - b.start_offset);
  const segments: TextSegment[] = [];
  let cursor = 0;

  for (const ev of sorted) {
    // Skip overlapping claims (take the first one)
    if (ev.start_offset < cursor) continue;
    if (ev.start_offset > cursor) {
      segments.push({ text: text.slice(cursor, ev.start_offset), evaluation: null });
    }
    segments.push({
      text: text.slice(ev.start_offset, ev.end_offset),
      evaluation: ev,
    });
    cursor = ev.end_offset;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), evaluation: null });
  }

  return segments;
}

export function DocumentViewer({ text, evaluations, selectedClaimId, onSelectClaim }: DocumentViewerProps) {
  const segments = buildSegments(text, evaluations);

  return (
    <div
      className="leading-7 text-base whitespace-pre-wrap"
      style={{ fontFamily: "var(--font-document)" }}
    >
      {segments.map((seg, i) => {
        if (!seg.evaluation) {
          return <span key={i}>{seg.text}</span>;
        }

        const color = UNDERLINE_COLORS[seg.evaluation.status];
        const isSelected = seg.evaluation.id === selectedClaimId;

        return (
          <span
            key={i}
            role="button"
            tabIndex={0}
            onClick={() => onSelectClaim(seg.evaluation!.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSelectClaim(seg.evaluation!.id);
            }}
            className="cursor-pointer transition-colors duration-150 rounded-sm hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
            style={{
              borderBottom: `3px solid ${color}`,
              backgroundColor: isSelected ? `${color}15` : "transparent",
              paddingBottom: "1px",
            }}
            aria-label={`Claim: ${seg.evaluation.status}`}
          >
            {seg.text}
          </span>
        );
      })}
    </div>
  );
}
