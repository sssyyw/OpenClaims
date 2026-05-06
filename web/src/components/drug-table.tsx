"use client";

import Link from "next/link";
import type { LabelDrug } from "@/lib/types";

export function DrugTable({ drugs }: { drugs: LabelDrug[] }) {
  if (drugs.length === 0) {
    return (
      <div className="text-center py-20 text-text-muted">
        <p className="text-lg font-medium">No drugs ingested yet</p>
        <p className="mt-2 text-sm">Upload an SPL XML file to get started.</p>
      </div>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border bg-surface-secondary/50 text-left">
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Drug Name</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Sections</th>
          <th className="py-3.5 px-6 text-xs font-semibold uppercase tracking-wider text-text-muted">Statements</th>
        </tr>
      </thead>
      <tbody>
        {drugs.map((d) => (
          <tr key={d.set_id} className="border-b border-border last:border-b-0 hover:bg-surface-secondary transition-colors duration-150">
            <td className="py-4 px-6">
              <Link href={`/labels/${d.set_id}`} className="font-medium text-primary hover:text-primary-hover">
                {d.drug_name}
              </Link>
            </td>
            <td className="py-4 px-6">{d.section_count}</td>
            <td className="py-4 px-6">{d.statement_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
