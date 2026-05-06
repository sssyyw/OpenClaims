"use client";

import Link from "next/link";
import type { LabelStatement } from "@/lib/types";

interface StatementsClientProps {
  drugName: string;
  statements: LabelStatement[];
}

export function StatementsClient({ drugName, statements }: StatementsClientProps) {
  // Group by section_name
  const sections = new Map<string, LabelStatement[]>();
  for (const s of statements) {
    const group = sections.get(s.section_name) || [];
    group.push(s);
    sections.set(s.section_name, group);
  }

  return (
    <div className="flex flex-col h-screen">
      <nav className="flex items-center gap-4 px-6 py-3.5 bg-surface/80 backdrop-blur-sm border-b border-border shadow-sm shrink-0">
        <Link href="/labels" className="text-sm font-medium text-text-muted hover:text-text transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-primary">
          &larr; Content Management
        </Link>
        <h1 className="text-base font-semibold tracking-tight text-text">{drugName}</h1>
        <span className="text-sm text-text-muted">
          {statements.length} statements across {sections.size} sections
        </span>
      </nav>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-10">
          {[...sections.entries()].map(([sectionName, sectionStatements]) => (
            <div key={sectionName}>
              <h2 className="sticky top-0 bg-bg/90 backdrop-blur-sm px-4 py-2.5 border-b border-border text-xs font-semibold text-text-muted uppercase tracking-wider z-10">
                {sectionName}
              </h2>
              <div className="space-y-3 mt-3">
                {sectionStatements.map((s) => (
                  <div key={s.id} className="p-5 bg-surface rounded-lg border border-border shadow-sm hover:shadow-md transition-shadow duration-200">
                    <p
                      className="text-sm leading-relaxed"
                      style={{ fontFamily: "var(--font-document)" }}
                    >
                      {s.statement_text}
                    </p>
                    <p className="mt-2 text-xs text-text-faint">
                      Ingested {new Date(s.ingested_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
