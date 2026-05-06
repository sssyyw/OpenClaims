# Annotated Review UI — Design Spec

## Overview

Frontend for the FDA Claims Intelligence POC. Three pages: review list, annotated document view, and upload flow. Built on Next.js 16 App Router with Tailwind 4. Desktop-only (1280px+).

## Pages

### 1. Review List (`/`)

Home screen. Table of review sessions ordered by date descending.

| Column | Source |
|--------|--------|
| Filename | `filename` |
| Drug Name | `drug_name` |
| Status | `status` badge (PROCESSING / IN_REVIEW / COMPLETE) |
| Claims | `total_claims` count |
| Reviewed | `reviewed_claims / total_claims` |
| Date | `created_at` |

**Upload flow:** Button opens file picker → uploads via `POST /api/claims/parse` with `drug_name` form field → on success, calls `POST /api/claims/evaluate/{document_id}` → redirects to `/reviews/[id]`.

**States:** skeleton rows while loading, "No reviews yet" empty state, error banner.

### 2. Annotated Document View (`/reviews/[id]`)

Two-column layout. This is the core experience.

**Left column (~65%):** Full document text (`extracted_text`) with colored underline highlights on each claim span using `start_offset`/`end_offset` character positions. Clicking a highlight selects that claim.

**Right panel (~35%, fixed position):** Shows detail for the selected claim:
- Quoted claim text at top
- Status badge (colored + text label)
- LLM reasoning paragraph
- Citation text in monospace + section reference
- Citation verified indicator
- Action buttons: Accept | Override | Escalate (text buttons, not filled)

**Override flow:** Clicking Override reveals a dropdown with 4 reasons (Label language is equivalent, Within fair balance, Supported by other section, Other) plus optional free-text detail field. Submit calls `POST /api/reviews/{id}/claims/{evalId}/decide`.

**Summary bar (bottom):** Horizontal status count breakdown — SUPPORTED: N, PARTIAL: N, REVIEW: N, UNSUPPORTED: N.

**Highlight colors:**
- Green `#198754` — SUPPORTED
- Blue `#0d6efd` — PARTIALLY_SUPPORTED
- Amber `#ffc107` — NEEDS_REVIEW
- Red `#dc3545` — UNSUPPORTED

### 3. Label Lookup Drawer

Slide-out from right (~40% width) within the review view. Shows label statements for the drug. Deferred to post-POC if time-constrained.

## API Client

Thin fetch wrapper. All endpoints return JSON.

```
GET  /api/reviews/              → { reviews: [...] }
GET  /api/reviews/{id}          → { review_id, document_id, filename, drug_name, extracted_text, status, evaluations: [...] }
POST /api/claims/parse          → FormData(file, drug_name) → { document_id, claims: [...] }
POST /api/claims/evaluate/{id}  → { review_id, evaluations: [...] }
POST /api/reviews/{id}/claims/{evalId}/decide → { decision_id, action, session_status }
```

## Visual Design

- **Background:** `#f8f9fa` (light gray)
- **Surface:** `#ffffff` (white)
- **Text:** `#1a1a2e` (near-black)
- **Muted text:** `#6c757d`
- **Document text:** Georgia, serif
- **UI chrome:** system sans-serif (Inter/system-ui)
- **Citations:** monospace
- **Spacing:** 4px base unit (4, 8, 12, 16, 24, 32)
- **No AI slop:** No gradients, sparkle icons, hero sections, or decorative illustrations

## Accessibility (POC scope)

- Color + text labels for all status badges
- Keyboard: Tab through claims, Enter to select, Escape to close drawers
- Visible focus rings on interactive elements
- ARIA landmarks for main regions
- 44px minimum touch targets
- WCAG AA contrast (4.5:1 text, 3:1 large text)

## Technical Decisions

- Next.js 16 App Router, React 19, Tailwind 4
- No additional UI libraries
- Client components for interactive pieces (claim selection, override form, actions)
- Server components for data fetching where possible
- API base URL configurable via env var
