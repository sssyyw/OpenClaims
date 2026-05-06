import type { ClaimEvaluation } from "@/lib/types";

export function SummaryBar({ evaluations }: { evaluations: ClaimEvaluation[] }) {
  const counts = {
    SUPPORTED: 0,
    PARTIALLY_SUPPORTED: 0,
    NEEDS_REVIEW: 0,
    UNSUPPORTED: 0,
  };
  for (const e of evaluations) {
    if (e.status in counts) counts[e.status]++;
  }

  const items = [
    { label: "SUPPORTED", count: counts.SUPPORTED, color: "var(--status-supported)" },
    { label: "PARTIAL", count: counts.PARTIALLY_SUPPORTED, color: "var(--status-partial)" },
    { label: "REVIEW", count: counts.NEEDS_REVIEW, color: "var(--status-review)" },
    { label: "UNSUP", count: counts.UNSUPPORTED, color: "var(--status-unsupported)" },
  ];

  return (
    <div className="flex items-center gap-8 px-6 py-3 bg-surface border-t border-border shadow-[0_-1px_3px_rgba(0,0,0,0.05)] text-xs font-medium tracking-wide">
      <span className="text-text-muted">{evaluations.length} claims</span>
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          {item.label}: {item.count}
        </span>
      ))}
    </div>
  );
}
