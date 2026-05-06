"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import type { ReviewDetail } from "@/lib/types";
import { DocumentViewer } from "@/components/document-viewer";
import { ClaimPanel } from "@/components/claim-panel";
import { SummaryBar } from "@/components/summary-bar";
import { getReview } from "@/lib/api";

interface ReviewClientProps {
  initialData: ReviewDetail;
}

export function ReviewClient({ initialData }: ReviewClientProps) {
  const [data, setData] = useState(initialData);
  const [selectedId, setSelectedId] = useState<string | null>(
    data.evaluations.length > 0 ? data.evaluations[0].id : null,
  );

  const selectedEval = data.evaluations.find((e) => e.id === selectedId) ?? null;

  const refresh = useCallback(async () => {
    const updated = await getReview(data.review_id);
    setData(updated);
  }, [data.review_id]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <nav aria-label="Review navigation" className="flex items-center gap-4 px-6 py-3.5 bg-surface/80 backdrop-blur-sm border-b border-border shadow-sm shrink-0">
        <Link href="/" className="text-sm font-medium text-text-muted hover:text-text transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-primary">
          &larr; Reviews
        </Link>
        <h1 className="text-base font-semibold tracking-tight text-text">{data.filename}</h1>
        {data.drug_name && (
          <span className="rounded-full bg-surface-secondary px-3 py-0.5 text-sm text-text-muted">{data.drug_name}</span>
        )}
      </nav>

      {/* Main content: two columns */}
      <div className="flex flex-1 min-h-0">
        {/* Left: document */}
        <main className="w-[65%] overflow-y-auto p-6 border-r border-border bg-bg" aria-label="Document text">
          {data.extracted_text ? (
            <DocumentViewer
              text={data.extracted_text}
              evaluations={data.evaluations}
              selectedClaimId={selectedId}
              onSelectClaim={setSelectedId}
            />
          ) : (
            <p className="text-text-muted">No document text available.</p>
          )}
        </main>

        {/* Right: claim detail */}
        <aside className="w-[35%] overflow-y-auto p-6 bg-surface" aria-label="Claim details">
          {selectedEval ? (
            <ClaimPanel
              key={selectedEval.id}
              evaluation={selectedEval}
              reviewId={data.review_id}
              onDecisionMade={refresh}
            />
          ) : (
            <p className="text-sm text-text-muted">Select a claim to view details.</p>
          )}
        </aside>
      </div>

      {/* Summary bar */}
      <SummaryBar evaluations={data.evaluations} />
    </div>
  );
}
