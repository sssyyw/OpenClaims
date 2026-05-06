import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryBar } from "../summary-bar";
import type { ClaimEvaluation } from "@/lib/types";

function makeEval(status: ClaimEvaluation["status"]): ClaimEvaluation {
  return {
    id: `eval-${Math.random()}`,
    claim_id: "c1",
    claim_text: "",
    start_offset: 0,
    end_offset: 1,
    status,
    reasoning: "",
    citation_text: null,
    citation_section: null,
    citation_verified: false,
    decision: null,
  };
}

describe("SummaryBar", () => {
  it("shows total claim count", () => {
    const evals = [makeEval("SUPPORTED"), makeEval("UNSUPPORTED")];
    render(<SummaryBar evaluations={evals} />);
    expect(screen.getByText("2 claims")).toBeDefined();
  });

  it("counts each status correctly", () => {
    const evals = [
      makeEval("SUPPORTED"),
      makeEval("SUPPORTED"),
      makeEval("PARTIALLY_SUPPORTED"),
      makeEval("NEEDS_REVIEW"),
      makeEval("UNSUPPORTED"),
      makeEval("UNSUPPORTED"),
    ];
    render(<SummaryBar evaluations={evals} />);

    expect(screen.getByText("6 claims")).toBeDefined();
    expect(screen.getByText(/SUPPORTED:\s*2/)).toBeDefined();
    expect(screen.getByText(/PARTIAL:\s*1/)).toBeDefined();
    expect(screen.getByText(/REVIEW:\s*1/)).toBeDefined();
    expect(screen.getByText(/UNSUP:\s*2/)).toBeDefined();
  });

  it("renders zero counts for missing statuses", () => {
    render(<SummaryBar evaluations={[]} />);
    expect(screen.getByText("0 claims")).toBeDefined();
    expect(screen.getByText(/SUPPORTED:\s*0/)).toBeDefined();
    expect(screen.getByText(/UNSUP:\s*0/)).toBeDefined();
  });
});
