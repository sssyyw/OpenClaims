"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReviews } from "@/lib/api";
import type { ReviewSummary } from "@/lib/types";
import { ReviewTable } from "@/components/review-table";
import { UploadForm } from "@/components/upload-form";

export default function Home() {
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReviews()
      .then(setReviews)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight text-text">Claims Intelligence</h1>
          <Link
            href="/labels"
            className="rounded-full px-3.5 py-1.5 text-sm font-medium text-text-muted hover:text-text hover:bg-surface-secondary transition-colors duration-150"
          >
            Content Management
          </Link>
        </div>
        <UploadForm />
      </div>
      <div className="bg-surface rounded-xl border border-border shadow-sm ring-1 ring-black/5 overflow-hidden">
        {loading ? (
          <div className="animate-pulse space-y-0">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-4 px-6 py-4 border-b border-border last:border-b-0">
                <div className="h-4 bg-border/50 rounded-md w-40" />
                <div className="h-4 bg-border/50 rounded-md w-24" />
                <div className="h-4 bg-border/50 rounded-md w-20" />
                <div className="h-4 bg-border/50 rounded-md w-12" />
                <div className="h-4 bg-border/50 rounded-md w-16" />
                <div className="h-4 bg-border/50 rounded-md w-20" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="py-20 text-center">
            <p className="text-unsupported font-medium">{error}</p>
          </div>
        ) : (
          <ReviewTable reviews={reviews} />
        )}
      </div>
    </div>
  );
}
