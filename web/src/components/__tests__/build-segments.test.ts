import { describe, it, expect } from "vitest";
import { buildSegments } from "../document-viewer";
import type { ClaimEvaluation } from "@/lib/types";

function makeEval(overrides: Partial<ClaimEvaluation> & Pick<ClaimEvaluation, "start_offset" | "end_offset">): ClaimEvaluation {
  return {
    id: "eval-1",
    claim_id: "claim-1",
    claim_text: "",
    status: "SUPPORTED",
    reasoning: "",
    citation_text: null,
    citation_section: null,
    citation_verified: false,
    decision: null,
    ...overrides,
  };
}

describe("buildSegments", () => {
  it("returns single segment when no evaluations", () => {
    const result = buildSegments("Hello world", []);
    expect(result).toEqual([{ text: "Hello world", evaluation: null }]);
  });

  it("returns empty array for empty text and no evaluations", () => {
    const result = buildSegments("", []);
    expect(result).toEqual([]);
  });

  it("wraps a single claim with before/after plain text", () => {
    const ev = makeEval({ start_offset: 6, end_offset: 11 });
    const result = buildSegments("Hello world here", [ev]);

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ text: "Hello ", evaluation: null });
    expect(result[1]).toEqual({ text: "world", evaluation: ev });
    expect(result[2]).toEqual({ text: " here", evaluation: null });
  });

  it("handles claim at start of text", () => {
    const ev = makeEval({ start_offset: 0, end_offset: 5 });
    const result = buildSegments("Hello world", [ev]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ text: "Hello", evaluation: ev });
    expect(result[1]).toEqual({ text: " world", evaluation: null });
  });

  it("handles claim at end of text", () => {
    const ev = makeEval({ start_offset: 6, end_offset: 11 });
    const result = buildSegments("Hello world", [ev]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ text: "Hello ", evaluation: null });
    expect(result[1]).toEqual({ text: "world", evaluation: ev });
  });

  it("handles claim spanning entire text", () => {
    const ev = makeEval({ start_offset: 0, end_offset: 5 });
    const result = buildSegments("Hello", [ev]);

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({ text: "Hello", evaluation: ev });
  });

  it("handles multiple non-overlapping claims", () => {
    const ev1 = makeEval({ id: "e1", start_offset: 0, end_offset: 5 });
    const ev2 = makeEval({ id: "e2", start_offset: 6, end_offset: 11 });
    const result = buildSegments("Hello world!", [ev1, ev2]);

    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({ text: "Hello", evaluation: ev1 });
    expect(result[1]).toEqual({ text: " ", evaluation: null });
    expect(result[2]).toEqual({ text: "world", evaluation: ev2 });
    expect(result[3]).toEqual({ text: "!", evaluation: null });
  });

  it("handles adjacent claims with no gap", () => {
    const ev1 = makeEval({ id: "e1", start_offset: 0, end_offset: 5 });
    const ev2 = makeEval({ id: "e2", start_offset: 5, end_offset: 10 });
    const result = buildSegments("HelloWorld", [ev1, ev2]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ text: "Hello", evaluation: ev1 });
    expect(result[1]).toEqual({ text: "World", evaluation: ev2 });
  });

  it("skips overlapping claims (keeps first by offset)", () => {
    const ev1 = makeEval({ id: "e1", start_offset: 0, end_offset: 8 });
    const ev2 = makeEval({ id: "e2", start_offset: 5, end_offset: 11 });
    const result = buildSegments("Hello world", [ev1, ev2]);

    // ev2 starts at 5 which is < cursor (8 after ev1), so ev2 is skipped
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ text: "Hello wo", evaluation: ev1 });
    expect(result[1]).toEqual({ text: "rld", evaluation: null });
  });

  it("sorts evaluations by start_offset regardless of input order", () => {
    const ev1 = makeEval({ id: "e1", start_offset: 6, end_offset: 11 });
    const ev2 = makeEval({ id: "e2", start_offset: 0, end_offset: 5 });
    // Passed in reverse order
    const result = buildSegments("Hello world", [ev1, ev2]);

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ text: "Hello", evaluation: ev2 });
    expect(result[1]).toEqual({ text: " ", evaluation: null });
    expect(result[2]).toEqual({ text: "world", evaluation: ev1 });
  });

  it("does not mutate the input evaluations array", () => {
    const ev1 = makeEval({ id: "e1", start_offset: 6, end_offset: 11 });
    const ev2 = makeEval({ id: "e2", start_offset: 0, end_offset: 5 });
    const input = [ev1, ev2];
    buildSegments("Hello world", input);

    expect(input[0].id).toBe("e1");
    expect(input[1].id).toBe("e2");
  });
});
