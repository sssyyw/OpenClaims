"use client";

import Link from "next/link";
import type { ReviewSummary } from "@/lib/types";
import { ReviewStatusBadge } from "@/components/status-badge";

export function ReviewTable({ reviews }: { reviews: ReviewSummary[] }) {
  if (reviews.length === 0) {
    return (
      <div className="text-center py-20 text-text-muted">
        <p className="text-lg font-medium">No reviews yet</p>
        <p className="mt-2 text-sm">Upload a promotional document to get started.</p>
      </div>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border bg-surface-secondary/50 text-left">
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Filename</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Drug</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Status</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Claims</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Reviewed</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Date</th>
        </tr>
      </thead>
      <tbody>
        {reviews.map((r) => (
          <tr key={r.id} className="border-b border-border last:border-b-0 hover:bg-surface-secondary transition-colors duration-150">
            <td className="py-4 px-6">
              <Link href={`/reviews/${r.id}`} className="font-medium text-primary hover:text-primary-hover">
                {r.filename}
              </Link>
            </td>
            <td className="py-4 px-6">{r.drug_name || "—"}</td>
            <td className="py-4 px-6"><ReviewStatusBadge status={r.status} /></td>
            <td className="py-4 px-6">{r.total_claims}</td>
            <td className="py-4 px-6">{r.reviewed_claims} / {r.total_claims}</td>
            <td className="py-4 px-6 text-text-muted">
              {new Date(r.created_at).toLocaleDateString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
