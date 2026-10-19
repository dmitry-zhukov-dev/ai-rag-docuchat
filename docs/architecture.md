# DocuChat — Architecture and Component Responsibilities

## 1. Purpose

DocuChat is a web application for uploading PDF and TXT documents, asking questions about their contents, and receiving answers with verifiable source references.

The application uses an existing Python backend, PostgreSQL for relational data, Qdrant for vector search, a local embedding model, and Gemini for answer generation.

This document describes the agreed architecture and responsibilities. The repository code remains the source of truth for the actual implementation status.

## 2. Agreed project structure

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
- Return the agreed API response schemas.
- Translate known application errors into appropriate HTTP responses.
- Avoid implementing substantial business logic directly in route handlers.

### `app/schemas/`

API contracts and data validation.

Responsibilities:
- Define request and response structures.
- Validate input and output data.
- Keep API contracts consistent with routes, services, and frontend consumers.
- Represent structured answers, insufficient-context status, and source metadata where required.

Do not assume a particular field exists until it is confirmed in the current code and the canonical plan.

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
- Support workspaces, documents, conversations, messages, and Evaluation entities as required by the canonical plan.

The final model graph and initial Alembic migration must be reconciled at Stage 14. Do not create intermediate migrations or apply schema changes during earlier development stages.

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

Existing integrations include the embedding implementation, Qdrant access, and Gemini generation. Langfuse is an additional planned integration.

Responsibilities:
- Encapsulate provider-specific APIs.
- Keep external SDK details out of unrelated layers.
- Handle provider-specific failures at appropriate boundaries.
- Keep optional observability from becoming a hard dependency for the core RAG workflow.

Do not assume every planned integration is already complete.

### `app/core/`

Shared application infrastructure.

Responsibilities include configuration, database/session infrastructure, security, and shared mechanisms that are already part of the existing design.

Extend the existing modules instead of introducing parallel infrastructure without a concrete need.

### `app/static/`

The existing frontend.

Responsibilities:
- Workspace management.
- Document upload, status display, selection, and deletion.
- Chat interaction and conversation history.
- Display of answers, insufficient-context state, and source references.
- Evaluation workflows and results.

Keep the frontend consistent with the actual API contracts. Do not assume an endpoint or response field exists without checking the backend.

### `tests/`

- `tests/unit/`: isolated component behavior.
- `tests/integration/`: interactions between application components.
- `tests/evaluation/`: retrieval, answer, and source-quality checks.

Tests can be authored and statically reviewed during implementation. Execution is prohibited until Stage 14 and explicit user authorization.

### `scripts/`

Existing project scripts and development utilities. Inspect their behavior before using them. Do not execute scripts that start services, contact external providers, mutate databases, or perform runtime checks while those actions are prohibited.

## 4. Existing RAG data flow

The current code audit identified the following high-level flow. Recheck exact signatures and behavior against the repository before modifying it.

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

The audit found that the current path includes `app/api/routes/chat.py`, `app/services/chat.py`, `app/rag/generation.py`, `app/rag/retrieval.py`, `app/rag/prompting.py`, and `app/integrations/llm.py`.

The exact behavior and contracts of these modules must be verified in the current repository before implementation changes.

## 5. Embeddings and vector search

The agreed embedding model is:

- Model: `intfloat/multilingual-e5-small`.
- Vector dimension: 384.
- Document embedding prefix: `passage:`.
- Query embedding prefix: `query:`.
- Inference: local embedding model, not Gemini embeddings.
- Vector storage and similarity search: Qdrant.

Do not replace the embedding model or change vector dimensions without explicit approval.

The final retrieval pipeline must preserve enough metadata to associate a retrieved result with its workspace, document, chunk, filename, and PDF page when applicable.

TXT documents must not receive fabricated page numbers.

## 6. Data and source attribution

A generated answer and its sources are different types of information.

The model produces answer text. The application must derive source identifiers and metadata from actual retrieved records, validate their access permissions, and return a structured result.

The target response contract is defined in `docs/mvp-v1-plan.md`. It includes the answer, insufficient-context status, and source references.

Source metadata must preserve, as applicable:
- `document_id`
- `filename`
- `page`
- `chunk_id`
- `snippet`

Do not trust a document ID, page number, or source reference invented by the language model. A valid source identifier also does not, by itself, prove that a claim is supported by that source.

The source and history design must account for reopening conversations and for documents that are subsequently deleted.

## 7. Storage responsibilities

### PostgreSQL

The relational database is responsible for persistent application records and relationships, including workspaces, documents, conversations, messages, and Evaluation data as required by the plan.

The final schema is assembled only at Stage 14.

### Qdrant

Qdrant stores vector points and retrieval metadata for document chunks.

Search must apply workspace and selected-document restrictions at the vector-search layer where required. Application-level ownership and readiness checks remain necessary.

The existence of a Qdrant point does not prove that its document is valid, accessible, or ready.

### File storage

The existing file-storage mechanism is responsible for uploaded document files. The application must distinguish the original filename from the internal storage path and must not accept arbitrary filesystem paths from clients.

The exact storage implementation must be confirmed from the repository rather than inferred from this architecture description.

## 8. Security boundaries

The application must isolate data between anonymous user sessions and their workspaces.

Ownership checks must cover workspaces, documents, conversations, messages, Evaluation cases, and Evaluation results.

A workspace ID or another object ID supplied by the client is not proof of authorization.

The application must validate access before returning or deleting records, files, and associated vector points. Qdrant filters complement, but do not replace, application-level authorization.

Session behavior, cookie settings, ownership enforcement, upload restrictions, and privacy requirements are defined in the canonical plan.

## 9. Evaluation and observability

Evaluation must use the real RAG retrieval and generation pipeline. It must persist actual answers, actual source references, execution status, and calculated metrics.

Deterministic metrics are the required baseline. An LLM-as-a-judge implementation is not part of the mandatory baseline without separate approval.

Langfuse v4 is an optional observability integration. Its unavailability must not prevent normal RAG operation. Full document text and secrets must not be sent to telemetry by default.

## 10. Database and migration policy

Database-dependent code may be implemented and ORM models may evolve throughout development.

Before Stage 14:
- Do not apply migrations.
- Do not create or rebuild the actual database schema.
- Do not create intermediate Alembic migrations.
- Do not perform destructive database or Docker-volume operations.
- Do not run the application or tests without explicit user authorization.

At Stage 14, reconcile all models, relationships, constraints, indexes, and Alembic metadata, then prepare one clean initial migration for the final schema.

## 11. Architectural change policy

Before proposing a structural change:
1. Identify the concrete problem.
2. Trace affected modules and callers.
3. Explain why the current architecture cannot address it adequately.
4. Describe the smallest viable alternative and its impact.
5. Obtain user approval when the change affects the agreed architecture or unresolved decisions.

Prefer targeted changes that preserve existing working code and API contracts wherever possible.
