"use client";

import { useState } from "react";
import type { OverrideReason } from "@/lib/types";

const OVERRIDE_REASONS: OverrideReason[] = [
  "Label language is equivalent",
  "Within fair balance",
  "Supported by other section",
  "Other",
];

interface OverrideFormProps {
  onSubmit: (reason: OverrideReason, detail?: string) => void;
  onCancel: () => void;
  saving: boolean;
}

export function OverrideForm({ onSubmit, onCancel, saving }: OverrideFormProps) {
  const [reason, setReason] = useState<OverrideReason>(OVERRIDE_REASONS[0]);
  const [detail, setDetail] = useState("");

  return (
    <div
      className="mt-3 p-4 rounded-lg border border-border bg-surface-secondary shadow-sm space-y-4"
      onKeyDown={(e) => { if (e.key === "Escape") onCancel(); }}
    >
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1.5">Reason</label>
        <select
          value={reason}
          onChange={(e) => setReason(e.target.value as OverrideReason)}
          className="w-full px-3 py-2 rounded-lg text-sm bg-surface shadow-sm ring-1 ring-border focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow duration-150"
        >
          {OVERRIDE_REASONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1.5">Detail (optional)</label>
        <textarea
          value={detail}
          onChange={(e) => setDetail(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg text-sm bg-surface shadow-sm ring-1 ring-border resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow duration-150"
          placeholder="Additional context..."
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onSubmit(reason, detail || undefined)}
          disabled={saving}
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-white shadow-sm hover:bg-primary-hover disabled:opacity-50 transition-colors duration-150"
        >
          {saving ? "Saving..." : "Submit Override"}
        </button>
        <button
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-text-muted rounded-lg hover:text-text hover:bg-surface transition-colors duration-150"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
