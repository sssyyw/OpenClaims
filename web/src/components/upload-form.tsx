"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { parseDocument, evaluateDocument } from "@/lib/api";

type UploadState = "idle" | "extracting" | "evaluating" | "error";

export function UploadForm() {
  const router = useRouter();
  const [state, setState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [drugName, setDrugName] = useState("");

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setState("extracting");

    try {
      const parsed = await parseDocument(file, drugName || undefined);
      setState("evaluating");
      const result = await evaluateDocument(parsed.document_id);
      router.push(`/reviews/${result.review_id}`);
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  const isProcessing = state === "extracting" || state === "evaluating";

  return (
    <div className="flex items-center gap-3">
      <input
        type="text"
        placeholder="Drug name (optional)"
        value={drugName}
        onChange={(e) => setDrugName(e.target.value)}
        className="px-3.5 py-2.5 rounded-lg text-sm bg-surface shadow-sm ring-1 ring-border placeholder:text-text-faint focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow duration-150"
      />
      <label className={`relative cursor-pointer px-4 py-2.5 rounded-lg text-sm font-medium shadow-sm ring-1 ring-border hover:bg-surface-secondary transition-all duration-150 ${isProcessing ? "animate-pulse" : ""}`}>
        {state === "idle" && "Upload Document"}
        {state === "extracting" && "Extracting claims..."}
        {state === "evaluating" && "Evaluating claims..."}
        {state === "error" && "Upload Document"}
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={handleUpload}
          className="absolute inset-0 opacity-0 cursor-pointer"
          disabled={isProcessing}
        />
      </label>
      {error && <span className="text-sm text-unsupported">{error}</span>}
    </div>
  );
}
