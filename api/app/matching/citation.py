"""Citation verification — hard gate for trust.

After the LLM generates a citation, verify that the quoted label passage exists
verbatim (or near-verbatim, >=95% character overlap) in the ingested label data.
If verification fails, downgrade to NEEDS_REVIEW.
"""


def verify_citation(citation_text: str, source_label_text: str) -> bool:
    """Check if the citation text exists in the source label with >=95% character overlap.

    Uses longest common substring ratio as a simple but effective measure.
    """
    if not citation_text or not source_label_text:
        return False

    citation_normalized = _normalize(citation_text)
    source_normalized = _normalize(source_label_text)

    if citation_normalized in source_normalized:
        return True

    overlap = _longest_common_substring_ratio(citation_normalized, source_normalized)
    return overlap >= 0.95


def _normalize(text: str) -> str:
    """Normalize whitespace and case for comparison."""
    return " ".join(text.lower().split())


def _longest_common_substring_ratio(a: str, b: str) -> float:
    """Ratio of the longest common substring length to the length of string a."""
    if not a:
        return 0.0

    # Dynamic programming approach for LCS
    m, n = len(a), len(b)
    max_len = 0

    # Space-optimized: only keep current and previous rows
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
                max_len = max(max_len, curr[j])
        prev = curr

    return max_len / m
