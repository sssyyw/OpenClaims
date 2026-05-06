import { describe, it, expect, vi, beforeEach } from "vitest";

// Must mock fetch before importing api module
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Dynamic import so the module sees our stubbed fetch
const { listReviews, getReview } = await import("../api");

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchJSON (via listReviews)", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ reviews: [{ id: "r1" }] }),
    });

    const result = await listReviews();
    expect(result).toEqual([{ id: "r1" }]);
  });

  it("throws on non-ok response with status and body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not Found"),
    });

    await expect(listReviews()).rejects.toThrow("API 404: Not Found");
  });

  it("calls the correct URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ reviews: [] }),
    });

    await listReviews();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/reviews/",
      undefined,
    );
  });
});

describe("getReview", () => {
  it("calls correct URL with review ID", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ review_id: "abc", evaluations: [] }),
    });

    const result = await getReview("abc");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/reviews/abc",
      undefined,
    );
    expect(result.review_id).toBe("abc");
  });
});
