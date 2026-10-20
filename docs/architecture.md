# DocuChat — Architecture and Component Responsibilities

## 1. Purpose

DocuChat is a web application for uploading PDF and TXT documents, asking questions about their contents, and receiving answers with verifiable source references.

The application uses an existing Python backend, PostgreSQL for relational data, Qdrant for vector search, a local embedding model, and Gemini for answer generation.

This document describes the implemented architecture and the responsibilities of each layer. The repository code remains the source of truth for exact behavior.

## 2. Project structure

```text
app/
├── core/
├── api/
│   └── routes/
├── schemas/
├── db/
│   └── models/
├── repositories/
├── services/
├── rag/
├── integrations/
└── static/

tests/
├── unit/
├── integration/
├── api/
└── evaluation/

scripts/
.env.example
Dockerfile
docker-compose.yml
README.md
requirements.txt
.gitignore
```

Preserve the existing structure. Do not add, remove, or reorganize architectural layers for cosmetic reasons.

## 3. Layer responsibilities

### `app/api/routes/`

HTTP entry points.

Responsibilities:
- Accept requests and validate request-level input.
- Invoke the appropriate services.
- Return the defined API response schemas.
- Translate known application errors into appropriate HTTP responses.
- Avoid implementing substantial business logic directly in route handlers.

### `app/schemas/`

API contracts and data validation.

Responsibilities:
- Define request and response structures.
- Validate input and output data.
- Keep API contracts consistent with routes, services, and frontend consumers.
- Represent structured answers, insufficient-context status, and source metadata where required.

Do not assume a particular field exists until it is confirmed in the current code.

### `app/services/`

Business logic and orchestration.

Responsibilities:
- Coordinate repositories, RAG operations, and external integrations.
- Enforce relevant business rules and ownership checks.
- Coordinate document and conversation workflows.
- Manage the application-level behavior of workspace, document, chat, and Evaluation operations.

Services must not rely on client-supplied object IDs as proof of ownership.

### `app/repositories/`

Relational data access.

Responsibilities:
- Read and write PostgreSQL-backed application entities.
- Encapsulate database queries and persistence operations.
- Keep query behavior consistent with the current ORM models and service contracts.

Do not move business workflows into repositories merely to reduce the number of service methods.

### `app/db/models/`

SQLAlchemy relational models.

Responsibilities:
- Represent persistent application entities.
- Define fields, relationships, constraints, and indexes as the implementation evolves.
- Support workspaces, documents, conversations, messages, and Evaluation entities as required by the application.

The model graph and the Alembic revisions in `migrations/versions/` must stay consistent. Apply schema changes through a new revision; do not edit migrations that have already been applied.

### `app/rag/`

RAG pipeline logic.

Responsibilities:
- Document loading.
- Text extraction and page metadata.
- Chunking.
- Retrieval orchestration.
- Prompt construction.
- Answer generation orchestration.
- Preservation and validation of source metadata.

Keep the relationship between each retrieved chunk and its originating document intact throughout the pipeline.

### `app/integrations/`

Adapters for external systems and model providers.

Existing integrations include the embedding implementation, Qdrant access, Gemini generation, and optional Langfuse tracing.

Responsibilities:
- Encapsulate provider-specific APIs.
- Keep external SDK details out of unrelated layers.
- Handle provider-specific failures at appropriate boundaries.
- Keep optional observability from becoming a hard dependency for the core RAG workflow.

### `app/core/`

Shared application infrastructure.

Responsibilities include configuration, database/session infrastructure, security, and shared mechanisms that are already part of the existing design.

Extend the existing modules instead of introducing parallel infrastructure without a concrete need.

### `app/static/`

The existing frontend.

Responsibilities:
- Bootstrap and restore of the default workspace and conversation for the anonymous session.
- Document upload, status display, and deletion.
- Chat interaction and conversation history.
- Display of answers, insufficient-context state, and source references.

Keep the frontend consistent with the actual API contracts. Do not assume an endpoint or response field exists without checking the backend.

### `tests/`

- `tests/unit/`: isolated component behavior.
- `tests/integration/`: interactions between application components.
- `tests/api/`: HTTP-level tests for sessions, workspaces, documents, and conversations.
- `tests/evaluation/`: evaluation service and metric computation.

Tests run against an in-memory SQLite database and stubbed providers, so they need neither Docker nor external services. Because two test modules share a basename, run the suite with `--import-mode=importlib` or run one test directory at a time.

### `scripts/`

Manual smoke and verification scripts. Most require running services (PostgreSQL, Qdrant, Gemini) and are not part of the automated test suite. Inspect a script before running it, because some scripts write test data to the configured services.

## 4. RAG data flow

The chat request follows this flow:

```text
HTTP chat route
    ↓
Chat service
    ↓
Workspace/document access and eligibility checks
    ↓
RAG answer orchestration
    ↓
Retrieval
    ↓
Qdrant integration
    ↓
Retrieved chunks and metadata
    ↓
Prompt construction
    ↓
Gemini generation
    ↓
Structured answer and source validation
    ↓
Chat service
    ↓
Message/history persistence
    ↓
Chat API response
    ↓
Frontend
```

The path is implemented in `app/api/routes/chat.py`, `app/services/chat.py`, `app/rag/generation.py`, `app/rag/retrieval.py`, `app/rag/prompting.py`, and `app/integrations/llm.py`.

## 5. Embeddings and vector search

The embedding model is:

- Model: `intfloat/multilingual-e5-small`.
- Vector dimension: 384.
- Document embedding prefix: `passage:`.
- Query embedding prefix: `query:`.
- Inference: local embedding model, not Gemini embeddings.
- Vector storage and similarity search: Qdrant.

Changing the embedding model or the vector dimension requires re-indexing the collection.

The retrieval pipeline preserves enough metadata to associate a retrieved result with its workspace, document, chunk, filename, and PDF page when applicable.

TXT documents have no page numbers; their page field is null.

## 6. Data and source attribution

A generated answer and its sources are different types of information.

The model produces answer text. The application must derive source identifiers and metadata from actual retrieved records, validate their access permissions, and return a structured result.

The response contract is defined in `app/schemas/chat.py`. It includes the answer, insufficient-context status, and source references.

Source metadata must preserve, as applicable:
- `document_id`
- `filename`
- `page`
- `chunk_id`
- `snippet`

Do not trust a document ID, page number, or source reference invented by the language model. A valid source identifier also does not, by itself, prove that a claim is supported by that source.

Source snapshots are stored with assistant messages, so reopening a conversation still shows citations after the underlying document is deleted.

## 7. Storage responsibilities

### PostgreSQL

The relational database is responsible for persistent application records and relationships, including workspaces, documents, conversations, messages, and Evaluation data.

The schema is versioned by the Alembic migrations in `migrations/versions/`.

### Qdrant

Qdrant stores vector points and retrieval metadata for document chunks.

Search must apply workspace and selected-document restrictions at the vector-search layer where required. Application-level ownership and readiness checks remain necessary.

The existence of a Qdrant point does not prove that its document is valid, accessible, or ready.

### File storage

`app/services/file_storage.py` validates uploads (extension, size) and stores them under `UPLOAD_DIR` with a random file name. The original filename and the internal storage path are kept separately on the document record, and the application never accepts arbitrary filesystem paths from clients.

## 8. Security boundaries

The application must isolate data between anonymous user sessions and their workspaces.

Ownership checks must cover workspaces, documents, conversations, messages, Evaluation cases, and Evaluation results.

A workspace ID or another object ID supplied by the client is not proof of authorization.

The application must validate access before returning or deleting records, files, and associated vector points. Qdrant filters complement, but do not replace, application-level authorization.

Session behavior, cookie settings, ownership enforcement, upload restrictions, and privacy requirements are configured in `app/core/config.py` and `.env.example`, and enforced in `app/core/security.py` and the API layer.

## 9. Evaluation and observability

Evaluation uses the real RAG retrieval and generation pipeline and persists the actual answer, the actual source references, execution status, and calculated metrics.

Deterministic metrics are the baseline; no LLM-as-a-judge evaluation is implemented.

Langfuse is an optional observability integration, implemented in `app/integrations/langfuse.py` and disabled by default. Its unavailability must not prevent normal RAG operation. Full document text and secrets are not sent to telemetry by default.

## 10. Database and migration policy

The relational schema is defined by the SQLAlchemy models and versioned by the Alembic revisions in `migrations/versions/`.

- Apply the current schema with `alembic upgrade head`.
- Introduce schema changes as new Alembic revisions; do not edit revisions that have already been applied.
- Keep the SQLAlchemy models and the migrations consistent.
- The Docker Compose `app` service does not apply migrations automatically; run the Alembic command during setup and after pulling new revisions.

## 11. Architectural change policy

Before proposing a structural change:
1. Identify the concrete problem.
2. Trace affected modules and callers.
3. Explain why the current architecture cannot address it adequately.
4. Describe the smallest viable alternative and its impact.

Prefer targeted changes that preserve existing working code and API contracts wherever possible.
