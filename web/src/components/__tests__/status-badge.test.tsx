import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ClaimStatusBadge, ReviewStatusBadge } from "../status-badge";
import type { ClaimStatus, ReviewStatus } from "@/lib/types";

describe("ClaimStatusBadge", () => {
  const cases: [ClaimStatus, string][] = [
    ["SUPPORTED", "SUPPORTED"],
    ["PARTIALLY_SUPPORTED", "PARTIAL"],
    ["NEEDS_REVIEW", "REVIEW"],
    ["UNSUPPORTED", "UNSUP"],
  ];

  it.each(cases)("renders '%s' status as '%s' label", (status, label) => {
    render(<ClaimStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeDefined();
  });
});

describe("ReviewStatusBadge", () => {
  const cases: [ReviewStatus, string][] = [
    ["PROCESSING", "PROCESSING"],
    ["IN_REVIEW", "IN REVIEW"],
    ["COMPLETE", "COMPLETE"],
  ];

  it.each(cases)("renders '%s' status as '%s' label", (status, label) => {
    render(<ReviewStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeDefined();
  });
});
