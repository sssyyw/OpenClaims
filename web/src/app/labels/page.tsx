"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { listLabelDrugs, searchLabelDrugs, ingestLabelFile } from "@/lib/api";
import type { LabelDrug } from "@/lib/types";
import { DrugTable } from "@/components/drug-table";

export default function LabelsPage() {
  const [drugs, setDrugs] = useState<LabelDrug[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const loadDrugs = useCallback(async (searchQuery?: string) => {
    setLoading(true);
    setError(null);
    try {
      const results = searchQuery
        ? await searchLabelDrugs(searchQuery)
        : await listLabelDrugs();
      setDrugs(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load drugs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDrugs();
  }, [loadDrugs]);

  function handleSearch(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadDrugs(value || undefined);
    }, 300);
  }

  async function handleIngest(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setIngesting(true);
    setError(null);
    try {
      await ingestLabelFile(file);
      await loadDrugs(query || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setIngesting(false);
      e.target.value = "";
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight text-text">Content Management</h1>
          <Link
            href="/"
            className="rounded-full px-3.5 py-1.5 text-sm font-medium text-text-muted hover:text-text hover:bg-surface-secondary transition-colors duration-150"
          >
            &larr; Reviews
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search drugs..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            className="px-3.5 py-2.5 rounded-lg text-sm bg-surface shadow-sm ring-1 ring-border placeholder:text-text-faint focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow duration-150"
          />
          <label className={`relative cursor-pointer px-4 py-2.5 rounded-lg text-sm font-medium shadow-sm ring-1 ring-border hover:bg-surface-secondary transition-all duration-150 ${ingesting ? "animate-pulse" : ""}`}>
            {ingesting ? "Ingesting..." : "Upload SPL"}
            <input
              type="file"
              accept=".xml"
              onChange={handleIngest}
              className="absolute inset-0 opacity-0 cursor-pointer"
              disabled={ingesting}
            />
          </label>
        </div>
      </div>
      <div className="bg-surface rounded-xl border border-border shadow-sm ring-1 ring-black/5 overflow-hidden">
        {loading ? (
          <div className="animate-pulse space-y-0">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-4 px-6 py-4 border-b border-border last:border-b-0">
                <div className="h-4 bg-border/50 rounded-md w-48" />
                <div className="h-4 bg-border/50 rounded-md w-16" />
                <div className="h-4 bg-border/50 rounded-md w-16" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="py-20 text-center">
            <p className="text-unsupported font-medium">{error}</p>
          </div>
        ) : (
          <DrugTable drugs={drugs} />
        )}
      </div>
    </div>
  );
}
