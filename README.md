# DocuChat

DocuChat is an educational MVP of a document-grounded chat application built with Retrieval-Augmented
Generation (RAG). You upload PDF or TXT files into a workspace, ask questions in natural language, and get
answers generated from retrieved passages. Every answer is returned with the document, page, chunk, and text
snippet it was grounded in.

The project is intentionally small and readable: a FastAPI backend, a minimal browser UI served by the same
process, PostgreSQL for relational data, Qdrant for vector search, a local multilingual embedding model, and
Google Gemini for answer generation.

> Status: working MVP for learning and portfolio purposes. It is not hardened for production use.

## Key features

- **Anonymous sessions.** The UI starts a session on load, identified by an HTTP-only cookie. Workspaces,
  documents, conversations, messages, and evaluation data are ownership-checked against that session on every
  request; a client-supplied object ID is never treated as proof of access.
- **PDF and TXT ingestion.** Page-aware PDF text extraction and UTF-8 TXT loading, with upload validation
  (extension and size) and per-conversation de-duplication by SHA-256 content hash.
- **Indexing status tracking.** Documents move through `processing`, `completed`, and `failed`; failed uploads
  can be retried without creating a duplicate record.
- **Local embeddings.** `intfloat/multilingual-e5-small` runs locally through `sentence-transformers`
  (384 dimensions, `passage:`/`query:` prefixes). No paid embedding API is used.
- **Workspace-scoped vector search.** Qdrant filters by workspace and, optionally, by the documents selected
  for a question. Retrieved chunks are re-validated against PostgreSQL before they reach the prompt.
- **Answers with verifiable sources.** Sources are derived from the chunks that were actually retrieved and
  stored, not from model output. They are persisted with the assistant message so history stays readable after
  a document is deleted.
- **Insufficient-context handling.** When no relevant chunk is retrieved, the API reports
  `insufficient_context: true` instead of calling the language model.
- **Conversation history and per-question document selection.** The prompt includes recent history, and a
  request can restrict retrieval to specific ready documents.
- **Evaluation mode.** Test cases run through the real retrieval and generation pipeline and produce
  deterministic retrieval, source-matching, and required-fact metrics; every run is stored.
- **Optional Langfuse tracing.** Disabled by default. When enabled, it traces retrieval and generation steps
  without transmitting document text, questions, or answers.

Out of scope for this MVP: OCR for scanned documents, web search, URL ingestion, a bundled document corpus,
user accounts, and streamed responses.

## Technology stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn, Pydantic v2, `pydantic-settings` |
| Relational storage | PostgreSQL 16, SQLAlchemy 2 ORM, Alembic migrations |
| Vector storage | Qdrant (`qdrant/qdrant:v1.19.2`), `qdrant-client` |
| Embeddings | `sentence-transformers` with `intfloat/multilingual-e5-small` (384-d) |
| Text extraction / chunking | `pypdf`, `langchain-text-splitters` |
| Answer generation | Google Gemini via `google-genai` |
| Observability | Langfuse (optional, off by default) |
| Frontend | Static HTML/CSS/JavaScript served by FastAPI |
| Tests | `pytest`, Starlette/FastAPI `TestClient`, `httpx` |
| Packaging | Dockerfile, Docker Compose |

## How the RAG pipeline works

The pipeline lives in `app/rag/` and `app/integrations/`; the chat workflow is orchestrated by
`app/services/chat.py`.

### 1. Upload and parsing

`POST /api/v1/workspaces/{workspace_id}/documents/upload?conversation_id=...` accepts a single PDF or TXT
file up to `MAX_FILE_SIZE_MB` (10 MB by default) for a specific conversation. The file is validated, stored
under `UPLOAD_DIR` with a random name, and hashed with SHA-256. A per-conversation claim
(`(conversation_id, file_hash)` is unique) prevents the same content from being indexed twice in one chat;
re-uploading an identical file returns the existing record instead of re-embedding it.

`app/rag/loaders.py` then extracts text:

- **PDF** — `pypdf` reads the file page by page and returns one segment per page with a 1-based page number.
  Empty pages are skipped. A PDF with no extractable text (for example, a scan without OCR) is rejected.
- **TXT** — the file is decoded as UTF-8 and returned as a single segment with `page = None`. Page numbers
  are never fabricated for text files.

Ingestion runs in a worker thread so status requests can still be served. The document is marked `completed`
on success, or `failed` with a short diagnostic message; vectors, the stored file, or both are cleaned up on
failure.

### 2. Text chunking

`app/rag/chunking.py` splits each page segment with LangChain's `RecursiveCharacterTextSplitter`: 1000
characters per chunk with 150 characters of overlap, preferring paragraph and line boundaries before falling
back to spaces and individual characters. Chunking happens per segment, so every chunk keeps the page it came
from. Empty chunks are discarded.

### 3. Embedding generation

`app/integrations/embeddings.py` wraps `intfloat/multilingual-e5-small`. The model is loaded lazily once per
process and cached. Chunks are embedded with the `passage: ` prefix and questions with the `query: ` prefix,
normalized, and produced in batches of 32. The output dimension is fixed at 384. The first embedding call
downloads the model weights from Hugging Face, so it needs internet access and takes noticeably longer than
later calls.

### 4. Vector retrieval through Qdrant

`app/integrations/qdrant.py` stores one point per chunk in a collection created on demand (`documents` by
default, cosine distance, 384 dimensions). Each point payload carries `workspace_id`, `document_id`,
`chunk_id`, `chunk_index`, `text`, `filename`, and `page`. Point IDs are derived deterministically with
UUID5 from `document_id:chunk_index`, so re-indexing a document overwrites its points instead of duplicating
them.

A question is embedded with the query prefix and searched with `query_points`. Filters are applied inside
Qdrant:

- the workspace ID is always required;
- an optional set of document IDs further restricts the search.

The default top-k is 5; the API accepts `limit` values from 1 to 20.

`app/rag/retrieval.py` then verifies the returned chunks against PostgreSQL. Chunks whose document no longer
exists, is not `completed`, or is outside the current selection are dropped and logged, so stale vector
points cannot leak into an answer.

### 5. Context construction and LLM generation

`app/rag/prompting.py` builds a single prompt from:

- instructions to answer only from the supplied context and history, to say when the answer is not in the
  documents, to treat retrieved text as data rather than instructions, and to answer in the language of the
  question;
- up to 100 stored messages of the conversation, in chronological order;
- the retrieved chunk texts;
- the current question.

`app/integrations/llm.py` sends the prompt to Gemini with `google-genai` using the configured `GEMINI_MODEL`.
Provider errors, timeouts, and empty responses are converted into a sanitized application error that the chat
route returns as HTTP 502; no answer is stored in that case. If retrieval returns no verified chunk at all,
the model is not called and the response is an empty answer with `insufficient_context: true`.

### 6. Source citations

Sources are built in `app/rag/generation.py` from the retrieved chunks themselves:

```json
{
  "document_id": "42",
  "filename": "handbook.pdf",
  "page": 7,
  "chunk_id": "42:3",
  "snippet": "…the first 300 characters of the retrieved chunk…"
}
```

`page` is `null` for TXT documents. The sources are returned with the chat response and stored as JSON on the
assistant message, so reopening a conversation still shows citations after the underlying document is
deleted. Citation metadata proves which passages were retrieved; it does not prove that the generated text is
fully supported by them.

## Architecture

```text
Browser (static UI)
        │  JSON over HTTP, session cookie
        ▼
FastAPI routes (app/api/routes)
        │  request validation, ownership checks
        ▼
Services (app/services) ────────► Repositories (app/repositories) ──► PostgreSQL
        │                                   ▲
        ▼                                   │ source verification
RAG pipeline (app/rag) ─► Integrations (app/integrations)
        │                     ├─ embeddings (local e5-small)
        │                     ├─ Qdrant (vector search)
        │                     ├─ Gemini (generation)
        │                     └─ Langfuse (optional tracing)
        ▼
Structured answer + sources ─► message persistence ─► API response
```

| Module | Responsibility |
|---|---|
| `app/main.py` | Creates the FastAPI app, configures CORS, registers routers, mounts the static UI. |
| `app/api/routes/` | HTTP endpoints, request validation, and error-to-status mapping. |
| `app/core/` | Settings, logging, anonymous sessions, and ownership checks (`security.py`). |
| `app/schemas/` | Pydantic request and response contracts. |
| `app/services/` | Business workflows: workspaces, documents, chat, conversations, evaluations, file storage. |
| `app/repositories/` | SQLAlchemy queries and persistence. |
| `app/db/models/` | ORM entities: sessions, workspaces, documents, conversations, messages, evaluation cases/runs. |
| `app/rag/` | Loading, chunking, retrieval, prompt construction, generation, and ingestion orchestration. |
| `app/integrations/` | Embedding model, Qdrant, Gemini, and the optional Langfuse tracer. |
| `app/static/` | Single-page browser UI. |
| `migrations/` | Alembic environment and schema revisions. |
| `docs/architecture.md` | Layer responsibilities, data flow, and design constraints. |
| `tests/` | Unit, integration, API, and evaluation tests. |
| `scripts/` | Manual smoke and verification scripts for local debugging. |

The JSON API is served under `/api/v1` (sessions, workspaces, documents, conversations, chat, evaluations).
Interactive OpenAPI documentation is available at `/docs`. Apart from `/health` and the root page, endpoints
require the session cookie; a missing or expired session returns HTTP 401.

## Project structure

```text
.
├── app/
│   ├── api/            # dependencies and HTTP routes
│   ├── core/           # configuration, security, logging
│   ├── db/             # SQLAlchemy base, engine/session, models
│   ├── integrations/   # embeddings, Qdrant, Gemini, Langfuse
│   ├── rag/            # loaders, chunking, retrieval, prompting, generation, ingestion
│   ├── repositories/   # PostgreSQL data access
│   ├── schemas/        # Pydantic contracts
│   ├── services/       # business logic and orchestration
│   ├── static/         # HTML, CSS, JavaScript UI
│   └── main.py         # FastAPI application entry point
├── docs/architecture.md
├── migrations/         # Alembic environment and revisions
├── scripts/            # manual smoke/verification scripts and sample documents
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── evaluation/
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Prerequisites

- Python 3.12 (the version used by the Docker image).
- Docker and Docker Compose for PostgreSQL and Qdrant.
- A Gemini API key.
- Internet access on the first run, both for installing dependencies and for downloading the embedding model.

## Local setup and configuration

### 1. Clone and install

```bash
git clone https://github.com/dmitry-zhukov-dev/ai-rag-docuchat.git
cd ai-rag-docuchat

python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Open `.env` and set `GEMINI_API_KEY`. Everything else has a working default for local development.

### 3. Environment variables

| Variable | Default / example | Purpose |
|---|---|---|
| `APP_NAME`, `APP_DESCRIPTION`, `APP_VERSION` | `DocuChat`, `Chat with your own documents`, `0.1.0` | Application metadata shown in OpenAPI. |
| `DATABASE_URL` | `postgresql+psycopg2://docuchat:docuchat@localhost:5433/docuchat` | PostgreSQL connection used by SQLAlchemy and Alembic. Port 5433 matches the Compose port mapping. |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST endpoint. |
| `QDRANT_COLLECTION` | `documents` | Collection name; created lazily on first ingestion. |
| `UPLOAD_DIR` | `uploads` | Directory for uploaded files. |
| `MAX_FILE_SIZE_MB` | `10` | Maximum upload size. |
| `ALLOWED_EXTENSIONS` | `.txt,.pdf` | Accepted file extensions. |
| `GEMINI_API_KEY` | *(empty)* | Gemini API key. Required only when an answer is generated. |
| `GEMINI_MODEL` | model name from `.env.example` | Generation model. Set it to a model enabled for your API key. |
| `SESSION_COOKIE_NAME` | `docuchat_session` | Anonymous session cookie name. |
| `SESSION_LIFETIME_DAYS` | `30` | Session and cookie lifetime. |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` when serving over HTTPS. |
| `SESSION_COOKIE_HTTPONLY` | `true` | Keeps the session cookie out of JavaScript. |
| `SESSION_COOKIE_SAMESITE` | `lax` | Cookie SameSite policy. |
| `CORS_ORIGINS` | `http://localhost,http://localhost:8000` | Explicit allowed origins. Needed only for a cross-origin frontend. |
| `LANGFUSE_ENABLED` | `false` | Enables optional tracing. |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | *(empty)* | Langfuse credentials, required only when tracing is enabled. |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse server. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `docuchat` | Database credentials used by Docker Compose to initialize PostgreSQL. Change them outside local development. |

**Configuring Gemini.** Create an API key in Google AI Studio and put it in `GEMINI_API_KEY`. The key is read
when the Gemini client is first created, so a missing key does not prevent the API from starting, but answer
generation will fail with HTTP 502. Set `GEMINI_MODEL` to a model that is available for your key; the value
shipped in `.env.example` is only a starting point and may need to be changed.

### 4. Start PostgreSQL and Qdrant

```bash
docker compose up -d postgres qdrant
```

This starts PostgreSQL 16 on host port `5433` and Qdrant on `6333` (REST) and `6334` (gRPC), with named
volumes for their data.

### 5. Apply the database migrations

```bash
alembic upgrade head
```

Alembic reads `DATABASE_URL` from `.env`. Both revisions in `migrations/versions/` are applied: the initial
schema and the chat-scoped document columns.

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

Open <http://localhost:8000> for the browser UI and <http://localhost:8000/docs> for the OpenAPI interface.
On load, the UI creates or reuses an anonymous session and resolves a default workspace and conversation.

### Alternative: run everything in Docker

```bash
cp .env.example .env   # set GEMINI_API_KEY
docker compose build
docker compose up -d postgres qdrant
docker compose run --rm app alembic upgrade head
docker compose up -d app
```

The `app` container receives container-network addresses automatically (`postgres:5432`, `qdrant:6333`), and
uploads are stored in a named volume. Database migrations are not applied automatically at container start,
so run the Alembic command once during setup and after pulling new revisions.

## Tests

Install the development dependencies first (`pip install -r requirements-dev.txt`). The tests use an
in-memory SQLite database through a FastAPI dependency override, and patch the Gemini client, the embedding
model, and Qdrant calls, so they need neither Docker, a Gemini key, nor network access.

```bash
# Full suite
pytest --import-mode=importlib

# Individual suites
pytest tests/unit
pytest tests/integration
pytest tests/api
pytest tests/evaluation
```

`tests/unit/test_security.py` and `tests/integration/test_security.py` share a module basename, so a plain
`pytest` run from the repository root stops with an import mismatch. Use `--import-mode=importlib` for a
single run, or run the test directories separately.

The suite covers:

- **Unit** — loaders, chunking, embeddings, retrieval, prompt construction, generation, Qdrant payloads,
  repositories, services, security helpers, and Langfuse guards.
- **Integration** — chat, upload/scope, document, evaluation, and security workflows through the API with a
  real (SQLite-backed) database session.
- **API** — sessions, workspaces, documents, and conversations.
- **Evaluation** — the evaluation service and metric computation with a mocked RAG pipeline.

These tests exercise application logic against stubs; they do not verify a live Gemini account, a live Qdrant
instance, or PDF rendering quality.

## Evaluation mode

Evaluation cases belong to a workspace and contain a question, an optional reference answer, required facts,
expected source references, and an optional document selection. Starting a run
(`POST /api/v1/evaluations/{case_id}/runs`) executes the same retrieval and generation pipeline as chat and
stores:

- the actual answer and the sources that were actually retrieved;
- a `completed` or `failed` status with an error message;
- deterministic metrics: retrieval hit rate, source precision, source recall, unexpected-source count, and
  required-fact coverage.

Runs are synchronous and kept in history. The reference answer is stored for reference but is not scored; the
metrics rely on token containment and source matching, not semantic grading.

## Limitations

- **External LLM dependency.** Answer generation requires a working Gemini API key and network access. Rate
  limits, quotas, or provider outages surface as HTTP 502 and no answer is stored.
- **Variable latency.** Ingestion is synchronous within the upload request (offloaded to a worker thread),
  and generation waits for the provider. The first embedding call after startup also loads the model.
  Response times therefore vary with document size, hardware, and provider load.
- **No OCR.** Image-only PDFs are rejected; there is no scanned-document support.
- **Anonymous access only.** There are no accounts or password recovery. Access is tied to the session
  cookie; clearing cookies loses access to existing data. The bundled UI manages a single default
  workspace/conversation, although the API supports more.
- **No streaming.** Answers are returned in a single response.
- **Fixed history window.** The prompt includes at most the first 100 stored messages of a conversation.
  Older conversations keep all messages for display, but later messages are not sent to the model.
- **Layered retrieval, not answer verification.** Sources show which chunks were retrieved and passed to the
  model; they do not independently verify every claim in the answer.
- **Deterministic metrics only.** Evaluation does not use an LLM judge, and the reference answer is not
  scored.
- **Fixed embedding configuration.** Changing the model or the 384-dimensional vectors requires re-indexing
  the collection.
- **Not production hardened.** There is no rate limiting, background job queue, or multi-instance ingestion
  coordination beyond the database claim. Uploads and evaluation runs are intended for single-node use.
- **Provider model names change.** `GEMINI_MODEL` must be a model that your API key can use.

## License

No license file is currently included in this repository. Add one before redistributing or reusing the code.
