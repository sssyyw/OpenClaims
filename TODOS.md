# TODOS

## Deferred from POC (2026-03-22 eng review)

### Multi-tenant auth
- **What:** Add Clerk or Auth0 for company-scoped tenancy with Reviewer/Admin/Agency roles
- **Why:** POC is single-user. Production needs multi-tenant access control for pharma companies + their agency partners.
- **Context:** Design doc specifies 3 roles (Reviewer, Admin, Agency reviewer). Agency reviewers are invited by company admins, scoped to specific drugs/materials. Start with Clerk — it has the best Next.js integration.
- **Depends on:** POC validation with real users

### 7-year data retention enforcement
- **What:** Implement data lifecycle policies aligned with 21 CFR Part 11
- **Why:** Pharma regulatory requirement. Uploaded materials and audit logs must be retained for 7 years. Deletion requests must be logged.
- **Context:** Design doc specifies retention policy. Implementation: soft delete with audit log entries. Actual data purging after 7 years via cron job.
- **Depends on:** Multi-tenant auth (need to scope retention per company)

### Ingestion failure alerting
- **What:** Surface staleness warnings when DailyMed data is >48 hours old
- **Why:** If the label data goes stale, reviewers might validate against outdated labeling. They need to know.
- **Context:** Design doc specifies: retries with exponential backoff, staleness warning on affected drug pages, log all failures.
- **Depends on:** Basic ingestion pipeline working

### P1 test coverage
- **What:** Add tests for DOCX extraction, drug lookup API, review decision logging
- **Why:** These codepaths exist in the POC but are lower priority than the core matching pipeline.
- **Context:** P0 tests cover SPL parsing, PDF extraction, claim extraction, semantic matching, citation verification, and e2e.
- **Depends on:** P0 tests passing

### Embedding model benchmarking
- **What:** Compare OpenAI text-embedding-3-large vs PubMedBERT on real label statements and promotional claims
- **Why:** Research shows generalist models can outperform domain-specific ones for short-context medical search. Need empirical data for our specific use case.
- **Context:** POC starts with OpenAI embeddings. Benchmark against PubMedBERT using a test set of ~50 promotional claims matched against label statements. Measure: retrieval precision@10, LLM evaluation quality downstream.
- **Depends on:** Ingestion pipeline + at least 1 therapeutic area of labels ingested

### LLM error handling hardening
- **What:** Add timeout handling and malformed response fallbacks for Claude API calls
- **Why:** Eng review identified 2 critical failure gaps: (1) API timeout during evaluation leaves partial results with no indication, (2) malformed LLM JSON silently drops claims.
- **Context:** Fix: timeout handler marks timed-out claims as NEEDS_REVIEW with "evaluation timed out" explanation. Defensive JSON parsing with fallback to NEEDS_REVIEW for unparseable responses.
- **Depends on:** Basic matching pipeline working

## Deferred from POC (2026-03-22 design review)

### Design system establishment
- **What:** Run /design-consultation to create a full DESIGN.md with color tokens, typography scale, component library, and interaction patterns
- **Why:** POC uses a minimal design brief (muted regulatory palette, serif document text, underline highlights with status badges). This is enough for one reviewer, but will drift into inconsistency as the product grows and more screens are added.
- **Context:** Design review established: regulatory-dense aesthetic, muted green/amber/red for status, Georgia/system serif for document text, 4px spacing scale. Formalize into DESIGN.md with component specs.
- **Depends on:** POC validation with real users

### Responsive/tablet support
- **What:** Add tablet breakpoints (768px-1279px) with intentional layout changes for the annotated document + right panel layout
- **Why:** POC is desktop-only (1280px+). If reviewers want to use this on tablets in meetings, the two-column layout (document + claim detail panel) needs a specific tablet treatment — not just stacking.
- **Context:** Design review scoped POC to desktop-only. Accessibility basics (keyboard nav, WCAG AA contrast, color+badge for status) are included in POC regardless.
- **Depends on:** POC validation + user feedback on device usage
