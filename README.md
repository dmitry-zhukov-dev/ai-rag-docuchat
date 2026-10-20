# DocuChat

DocuChat is a web application where users upload their own PDF and TXT documents, ask questions about their contents, and receive answers with verifiable sources (filename, page number, and text snippet).

## Features

- Workspace creation and management.
- PDF/TXT uploads with page-aware text extraction, chunking, embeddings, and Qdrant indexing.
- Document processing status tracking (`processing`, `completed`, `failed`).
- Question answering with the local `intfloat/multilingual-e5-small` embedding model and Gemini generation.
- Answers with verifiable sources: document, filename, page, chunk identifier, and text snippet.
- Insufficient-context detection when the documents do not contain the answer.
- Conversation and message history with persisted sources.
- Per-question document selection.
- Anonymous session isolation (cookie-based) across workspaces, documents, conversations, and evaluation data.
- Evaluation mode that runs the real RAG pipeline and computes deterministic retrieval, answer, and source metrics.
- Optional Langfuse tracing (disabled by default).
- A complete browser interface served by the API itself.

Out of scope for the MVP: OCR for scanned documents, internet search, ingestion from URLs, a built-in document corpus, and markdown as a separate format.

## Prerequisites

- Python 3.12
- Docker & Docker Compose (for PostgreSQL and Qdrant)
- A Gemini API key (`GEMINI_API_KEY`)

## Development setup

1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
5. Start the infrastructure:
   ```bash
   docker compose up -d
   ```
6. Apply the final database migration once (see Stage 14 note below):
   ```bash
   alembic upgrade head
   ```
7. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
8. Open http://localhost:8000. The browser workflow is self-serving: the first request creates an anonymous session through a secure cookie.

When running through Docker Compose, the `app` service uses the container-network addresses (`postgres:5432`, `qdrant:6333`) automatically.

## Architecture

```text
app/
├── core/          configuration, sessions, security
├── api/routes/    HTTP endpoints (input validation only)
├── schemas/       API contracts (Pydantic)
├── services/      business logic and orchestration
├── repositories/  PostgreSQL data access
├── db/models/     SQLAlchemy models
├── rag/           loading, chunking, retrieval, prompting, generation
├── integrations/  embeddings, Qdrant, Gemini, Langfuse
└── static/        browser interface
```

The RAG data flow: chat route → chat service (ownership and readiness checks) → retrieval (Qdrant, workspace-filtered) → source verification against PostgreSQL → prompt construction → Gemini generation → structured answer with sources → message persistence.

## Configuration

All settings are documented in `.env.example`: database and Qdrant URLs, Gemini model, upload limits, session/cookie settings, CORS origins, and Langfuse. Embeddings always use the local `intfloat/multilingual-e5-small` model (384 dimensions, `passage:`/`query:` prefixes); no paid embedding API is used.

## Evaluation mode

Evaluation test cases (question, optional reference answer, required facts, expected sources, selected documents) are stored per workspace. Starting a run executes the same RAG pipeline as chat and stores the actual answer, the actual sources, and deterministic metrics (retrieval hit rate/precision/recall, required-fact coverage, source matching). Every run is preserved in history.

## Langfuse

Set `LANGFUSE_ENABLED=true` and provide `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` to trace question processing as separate retrieval and generation steps. The integration is optional: the RAG pipeline works without it. By default no question, document, or answer content is transmitted.

## MVP limitations

- Anonymous sessions only (no user accounts).
- Evaluation runs are synchronous.
- Scanned/image-only PDFs are not supported (no OCR).
- The Gemini model name must be verified against the provider before final launch.

## Project status

The MVP v1 implementation is complete according to `docs/mvp-v1-plan.md`. Runtime verification (database assembly, migrations, end-to-end workflows, and the full test suite) is intentionally deferred to Stage 14 and requires explicit authorization; see `docs/mvp-v1-plan.md` for the current status of every stage.

## Tests

Tests are prepared but must not be executed before Stage 14 and explicit authorization (see `AGENTS.md` and the canonical plan). When authorized:

```bash
pytest
```
