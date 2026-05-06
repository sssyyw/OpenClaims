"""Tests for citation verification — the trust hard gate."""

from app.matching.citation import verify_citation


class TestCitationVerification:
    def test_exact_match(self):
        citation = "KEYTRUDA is indicated for the treatment of patients"
        source = "KEYTRUDA is indicated for the treatment of patients with advanced melanoma."
        assert verify_citation(citation, source) is True

    def test_near_match_whitespace_differences(self):
        citation = "KEYTRUDA  is  indicated  for  the  treatment"
        source = "KEYTRUDA is indicated for the treatment of patients."
        assert verify_citation(citation, source) is True

    def test_near_match_case_insensitive(self):
        citation = "keytruda is indicated for the treatment of patients"
        source = "KEYTRUDA is indicated for the treatment of patients with advanced melanoma."
        assert verify_citation(citation, source) is True

    def test_no_match_hallucinated_citation(self):
        citation = "KEYTRUDA cures all forms of cancer permanently"
        source = "KEYTRUDA is indicated for the treatment of patients with advanced melanoma."
        assert verify_citation(citation, source) is False

    def test_partial_match_below_threshold(self):
        citation = "KEYTRUDA reduces mortality by 30% in all patient populations"
        source = "KEYTRUDA demonstrated a reduction in all-cause mortality."
        assert verify_citation(citation, source) is False

    def test_empty_citation(self):
        assert verify_citation("", "some source text") is False

    def test_empty_source(self):
        assert verify_citation("some citation", "") is False

    def test_both_empty(self):
        assert verify_citation("", "") is False
