# Groww Weekly Review Pulse

Automated weekly pipeline that turns **Groww** Google Play Store reviews into a one-page insight report, delivered via in-project Google Docs and Gmail MCP servers.

## Documentation

- [Problem Statement](docs/ProblemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Edge Cases](docs/edge-cases.md)

## Requirements

- Python 3.11+
- Windows, macOS, or Linux

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Install package + dev + reasoning stack
pip install -e ".[dev,reasoning]"

# Environment variables (Groq API key for analyze)
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
# Edit .env and set GROQ_API_KEY=...
```

## Configuration

Non-secret settings live in `config/`:

| File | Purpose |
|---|---|
| `config/groww.yaml` | Groww package ID, Google Doc ID, email recipients |
| `config/pulse.yaml` | Review window, preprocess, **BGE embeddings**, clustering, Groq LLM |

**Secrets do not belong in `pulse/` or committed YAML.**

| Secret | Where |
|---|---|
| Groq API key | `.env` → `GROQ_API_KEY` (copy from `.env.example`) |
| Google OAuth (Docs/Gmail) | `mcp-servers/google-docs-mcp/auth/`, `mcp-servers/gmail-mcp/auth/` (gitignored) |

Before delivery, replace `REPLACE_WITH_STAGING_OR_PROD_DOC_ID` in `config/groww.yaml` with a real Google Doc ID.

## CLI

```bash
# Help
python -m pulse --help

# Validate configuration
python -m pulse config

# Ingest Groww Play Store reviews → two files under data/
#   reviews_raw.json        — all fetched reviews (~9.7k for 12-week window)
#   reviews_normalized.json — filtered (~1.5k: 8+ words, no emoji, Roman script)
python -m pulse ingest --product groww --week 2026-W25
python -m pulse ingest --product groww --week 2026-W25 --force-refresh

# Future pipeline commands
python -m pulse analyze --product groww --week 2026-W25
python -m pulse run --product groww --week 2026-W25
```

## Project layout

```
pulse/           Pulse agent (MCP client) — no Google credentials
mcp-servers/     Google Docs + Gmail MCP servers (Phases 4–5)
config/          Product and pipeline YAML
.env.example     Template for GROQ_API_KEY (copy to .env)
data/            Runtime cache and ledger (gitignored)
  reviews_raw.json
  reviews_normalized.json
  embeddings_{run_id}.parquet
  report_{run_id}.json
scripts/         Scheduler hooks
docs/            Design documents
```

## Development

```bash
# Tests
pytest

# Lint
ruff check pulse tests

# Dashboard UI (Stitch design)
cd frontend && npm install && npm run dev
```

See [frontend/README.md](frontend/README.md) for the React dashboard (6 screens, Luminous Fintech theme).

## Phase status

| Phase | Status |
|---|---|
| 0 — Foundation | Complete |
| 1 — Ingestion | Complete |
| 1 — Preprocessing | Complete (normalize + PII scrub) |
| 2 — Reasoning | Complete (BGE + UMAP + HDBSCAN + Groq) |
| 3 — Rendering | Planned |
| 4–8 | Planned |

## Tech stack (reasoning)

| Component | Choice |
|---|---|
| Embeddings | **BGE** — `BAAI/bge-small-en-v1.5` (default) or `BAAI/bge-large-en-v1.5` |
| Clustering | UMAP + HDBSCAN |
| LLM | Groq — `llama-3.3-70b-versatile` (`GROQ_API_KEY` in `.env`) |
| Preprocess | `min_words: 8`, script filter (keep Roman Hinglish), PII regex |

See [architecture.md](docs/architecture.md) for full design and Groq rate limits.
