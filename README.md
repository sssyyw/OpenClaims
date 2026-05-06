# FDA Claims Intelligence


## Quick Start

```bash
# 1. Database (one-time)
createdb claims_intelligence
psql claims_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2. API server
cd api
source .venv/bin/activate
uvicorn app.main:app --reload          # http://localhost:8000

# 3. Frontend (new terminal)
cd web
npm run dev                             # http://localhost:3000

# 4. Ingest drug labels (one-time, requires OpenAI API key)
cd api
source .venv/bin/activate
python scripts/ingest.py /path/to/spl-xml-files/
```

Open http://localhost:3000 -- upload a promotional PDF/DOCX, the system extracts claims, evaluates each against FDA labels, and presents an annotated document for review.

## Architecture

```
ideas/
├── api/          Python FastAPI backend (PostgreSQL + pgvector)
└── web/          Next.js 16 frontend (React 19, Tailwind 4)
```

**Pipeline:** Upload promotional PDF/DOCX → extract claims with LLM → embed claims → pgvector similarity search against drug label statements → LLM evaluation with citation → citation verification → reviewer accept/override/escalate.

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- OpenAI API key (embeddings)
- Anthropic API key (claim extraction + evaluation)

## Setup

### Database

```bash
createdb claims_intelligence
psql claims_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # edit with your API keys
```

### Frontend

```bash
cd web
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
```

## Running

```bash
# Terminal 1: API server
cd api && source .venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2: Frontend dev server
cd web && npm run dev
```

- API: http://localhost:8000
- Frontend: http://localhost:3000

## Environment Variables

Configured in `api/.env` with `CI_` prefix (also reads standard env vars as fallback).

| Variable | Default | Description |
|----------|---------|-------------|
| `CI_DATABASE_URL` | `postgresql+asyncpg://localhost:5432/claims_intelligence` | PostgreSQL connection |
| `CI_ANTHROPIC_API_KEY` | — | Anthropic API key for Claude |
| `CI_OPENAI_API_KEY` | — | OpenAI API key for embeddings |
| `CI_EMBEDDING_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `CI_EMBEDDING_DIMENSIONS` | `1536` | Embedding vector dimensions |
| `CI_LLM_MODEL` | `claude-sonnet-4-20250514` | Claude model for evaluation |
| `CI_LLM_MAX_CONCURRENT` | `5` | Max parallel LLM calls |
| `CI_LLM_TIMEOUT_SECONDS` | `30` | LLM request timeout |
| `CI_RETRIEVAL_TOP_K` | `10` | Top-K label statements per claim |

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |

### Labels (Content Management)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/labels/drugs` | List all ingested drugs with section/statement counts |
| GET | `/api/labels/drugs/search?q=` | Search drugs by name (case-insensitive) |
| GET | `/api/labels/drugs/{set_id}/statements` | Get all label statements for a drug |
| POST | `/api/labels/ingest/file` | Upload and ingest an SPL XML file |
| POST | `/api/labels/ingest/directory` | Ingest all SPL files from a local directory |

### Claims

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/claims/parse` | Upload promotional doc (PDF/DOCX), extract text + claims |
| POST | `/api/claims/evaluate/{document_id}` | Run matching pipeline on all claims in a document |

`POST /api/claims/parse` accepts `multipart/form-data` with `file` (required) and `drug_name` (optional query param). Returns document ID, extracted claims with character offsets.

`POST /api/claims/evaluate/{document_id}` runs: embed claims → pgvector retrieval → Claude evaluation → citation verification. Returns review session with all evaluations.

### Reviews

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reviews/` | List all review sessions |
| GET | `/api/reviews/{review_id}` | Get review with evaluations and decisions |
| POST | `/api/reviews/{review_id}/claims/{evaluation_id}/decide` | Record accept/override/escalate decision |

Decision request body:
```json
{
  "action": "ACCEPT | OVERRIDE | ESCALATE",
  "override_reason": "Label language is equivalent | Within fair balance | Supported by other section | Other",
  "override_detail": "optional free text"
}
```

Review sessions auto-complete when all claims have decisions.

## Scripts

### SPL Label Ingestion

Ingest FDA drug labels (SPL XML format) into the vector store.

```bash
cd api && source .venv/bin/activate

# Single file
python scripts/ingest.py /path/to/label.xml

# Directory of XML/ZIP files (supports DailyMed bulk downloads)
python scripts/ingest.py /path/to/spl-directory/
```

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Review list home -- table of review sessions, upload promotional docs |
| `/reviews/[id]` | Annotated document view -- inline claim highlights, detail panel, accept/override/escalate |
| `/labels` | Content management -- list ingested drugs, search, upload SPL files |
| `/labels/[set_id]` | Drug detail -- label statements grouped by section |

## Tests

```bash
cd api && source .venv/bin/activate
python -m pytest tests/ -v    # 64 tests
```

Test suites: SPL parser, statement extraction, label ingestion, document parsing, citation verification, semantic matching pipeline.

## Claim Statuses

| Status | Meaning |
|--------|---------|
| SUPPORTED | Claim is directly supported by FDA label |
| PARTIALLY_SUPPORTED | Claim has some support but not fully |
| NEEDS_REVIEW | Requires manual reviewer attention |
| UNSUPPORTED | No label support found |

Claims with unverified citations are automatically downgraded to NEEDS_REVIEW.

## Review Statuses

| Status | Meaning |
|--------|---------|
| PROCESSING | Claims being evaluated |
| IN_REVIEW | Evaluation complete, awaiting reviewer decisions |
| COMPLETE | All claims reviewed |
