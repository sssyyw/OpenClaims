"use client";

import { useState } from "react";
import type { ClaimEvaluation, ReviewAction, OverrideReason } from "@/lib/types";
import { ClaimStatusBadge } from "@/components/status-badge";
import { OverrideForm } from "@/components/override-form";
import { decideClaim } from "@/lib/api";

interface ClaimPanelProps {
  evaluation: ClaimEvaluation;
  reviewId: string;
  onDecisionMade: () => void;
}

export function ClaimPanel({ evaluation, reviewId, onDecisionMade }: ClaimPanelProps) {
  const [showOverride, setShowOverride] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAction(
    action: ReviewAction,
    overrideReason?: OverrideReason,
    overrideDetail?: string,
  ) {
    setSaving(true);
    setError(null);
    try {
      await decideClaim(reviewId, evaluation.id, action, overrideReason, overrideDetail);
      setShowOverride(false);
      onDecisionMade();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save decision");
    } finally {
      setSaving(false);
    }
  }

  const hasDecision = evaluation.decision !== null;

  return (
    <div className="space-y-5">
      {/* Claim text */}
      <div
        className="p-4 bg-surface-secondary rounded-lg border-l-4 shadow-sm text-sm leading-relaxed"
        style={{
          fontFamily: "var(--font-document)",
          borderLeftColor: "var(--border-strong)",
        }}
      >
        {evaluation.claim_text}
      </div>

      {/* Status */}
      <div className="flex items-center gap-2">
        <ClaimStatusBadge status={evaluation.status} />
        {evaluation.citation_verified && (
          <span className="text-xs font-medium text-supported">Citation verified</span>
        )}
        {evaluation.citation_text && !evaluation.citation_verified && (
          <span className="text-xs font-medium text-unsupported">Citation unverified</span>
        )}
      </div>

      {/* Reasoning */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">Reasoning</h4>
        <p className="text-sm leading-relaxed">{evaluation.reasoning}</p>
      </div>

      {/* Citation */}
      {evaluation.citation_text && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
            Citation
            {evaluation.citation_section && (
              <span className="font-normal normal-case tracking-normal"> — {evaluation.citation_section}</span>
            )}
          </h4>
          <p
            className="text-sm leading-relaxed p-3 bg-surface-secondary rounded-lg border border-border shadow-sm"
            style={{ fontFamily: "var(--font-citation)" }}
          >
            {evaluation.citation_text}
          </p>
        </div>
      )}

      {/* Decision badge if already decided */}
      {hasDecision && (
        <div className="p-3 bg-surface-secondary rounded-lg border border-border text-sm">
          Decision: <span className="font-semibold">{evaluation.decision!.action}</span>
          {evaluation.decision!.override_reason && (
            <span className="text-text-muted"> — {evaluation.decision!.override_reason}</span>
          )}
        </div>
      )}

      {/* Action buttons */}
      {!hasDecision && (
        <div>
          <div className="flex gap-2">
            <button
              onClick={() => handleAction("ACCEPT")}
              disabled={saving}
              className="min-h-[44px] px-5 py-2.5 text-sm font-semibold rounded-lg border border-supported text-supported shadow-sm hover:bg-supported/10 disabled:opacity-50 transition-all duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-supported"
            >
              Accept
            </button>
            <button
              onClick={() => setShowOverride(!showOverride)}
              disabled={saving}
              className="min-h-[44px] px-5 py-2.5 text-sm font-semibold rounded-lg border border-primary text-primary shadow-sm hover:bg-primary/10 disabled:opacity-50 transition-all duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
            >
              Override
            </button>
            <button
              onClick={() => handleAction("ESCALATE")}
              disabled={saving}
              className="min-h-[44px] px-5 py-2.5 text-sm font-semibold rounded-lg border border-border text-text-muted shadow-sm hover:bg-surface-secondary disabled:opacity-50 transition-all duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
            >
              Escalate
            </button>
          </div>
          {showOverride && (
            <OverrideForm
              onSubmit={(reason, detail) => handleAction("OVERRIDE", reason, detail)}
              onCancel={() => setShowOverride(false)}
              saving={saving}
            />
          )}
          {error && <p className="mt-2 text-sm text-unsupported">{error}</p>}
        </div>
      )}
    </div>
  );
}
