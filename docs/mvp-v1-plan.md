# DocuChat — MVP v1 canonical implementation plan

> This document is the canonical source of truth for MVP v1 requirements, implementation order, restrictions, and acceptance criteria. Preserve all stages from 0 through 14. Do not shorten or replace the plan with a newly invented roadmap.

## Current project status

| Stage | Status | Current understanding |
|---|---|---|
| 0. Audit and baseline | Completed | The initial repository audit was completed. Repeat it only when needed to establish the current branch, working tree, and actual code state. |
| 1. Ingestion pipeline | Implementation completed; runtime unverified | Page-aware PDF/TXT loading and chunk metadata changes were implemented and statically reviewed. Tests were updated but have not been executed. |
| 2. Retrieval and Qdrant metadata | Partially implemented | Page metadata is stored and returned. Workspace/document filtering and all required metadata must be audited against the complete requirements. |
| 3. RAG generation | In progress / next focus | Audit retrieval, context construction, Gemini generation, error handling, insufficient-context behavior, and structured results. Preserve actual source metadata. |
| 4. Sources and conversation history | Not started as a complete stage | Implement verifiable sources and ensure source information survives history persistence and retrieval. |
| 5. Session security and isolation | Not started as a complete stage | Audit and implement session-based ownership checks throughout the API and services. |
| 6. Document selection | Not started | Add explicit document selection semantics and enforce them in retrieval. |
| 7. Operation reliability | Not started | Address partial failures and consistency across PostgreSQL, files, and Qdrant. |
| 8. Frontend | Not started as a complete stage | Complete the browser workflow against the real API contracts. |
| 9. Evaluation mode | Not started as a complete stage | Implement real RAG evaluation, deterministic metrics, persistence, and UI. |
| 10. Langfuse v4 | Not started as a complete stage | Add optional, privacy-conscious tracing without making Langfuse mandatory. |
| 11. Test preparation | Not started as a complete stage | Prepare and statically review tests. Do not execute them before Stage 14 and explicit user authorization. |
| 12. Configuration and Docker | Not started as a complete stage | Reconcile Python version, dependencies, environment configuration, and container setup. |
| 13. Documentation and final static audit | Not started | Reconcile code, contracts, configuration, tests, architecture, and documentation before final database assembly. |
| 14. Final database, launch, and acceptance | Partially completed (Database aligned & persistence verified) | PostgreSQL schema cleanly migrated to c4f1a2b3d4e5 head, pre-migration backup verified, and persistence verified via repositories. Application launch and RAG smoke test pending user authorization. |

## Important status rules

These statuses are an initial working snapshot, not proof of runtime correctness.

- Update the table only when repository evidence supports the change.
- Do not mark a stage complete merely because code has been written.
- Clearly distinguish implementation, static review, and runtime verification.
- Preserve the complete detailed requirements below this status block.
- Do not reorder stages or move final database assembly earlier.
- Record blockers, unresolved decisions, changed files, and remaining acceptance criteria for each task.

## Non-negotiable database and runtime restrictions

Until Stage 14 and explicit user authorization, do not run the application, Swagger, tests, runtime scripts, database migrations, schema creation/rebuilds, or destructive Docker-volume operations.

The implementation of database-dependent features may continue, but intermediate Alembic migrations must not be created or applied. The final database schema and clean initial migration are prepared at Stage 14.

---

## Canonical detailed plan

The complete detailed plan follows. Its requirements, subtask descriptions, unresolved decisions, exclusions, and acceptance criteria must be preserved.

# DocuChat — MVP v1 Completion Plan

## 1. Project Goal

DocuChat is a web application where users upload their own PDF and TXT documents, ask questions about their contents, and receive answers with verifiable sources.

### Required MVP Features

1. Workspace creation and management.
2. PDF/TXT uploads, document processing, and status tracking.
3. Text extraction, chunking, embeddings, and indexing in Qdrant.
4. Relevant chunk retrieval and answer generation through Gemini.
5. Answers with verifiable sources, page numbers, and text snippets.
6. Conversation and message history.
7. Document selection for individual questions.
8. Data isolation between user sessions and workspaces.
9. Evaluation mode for assessing RAG quality.
10. Langfuse v4 integration.
11. A complete web interface.
12. Unit, integration, security, and evaluation tests.
13. Consistent configuration, Docker setup, README, and startup instructions.

### Out of Scope for the MVP

- OCR for scanned documents.
- Internet search.
- Document ingestion from arbitrary URLs.
- A built-in document corpus.
- Markdown support as a separate document format.
- Mandatory paid APIs or services.

---

## 2. Architecture and Project Structure

Preserve the existing architecture. Do not perform major restructuring without separate approval.

```text
app/
├── core/
├── api/routes/
├── schemas/
├── db/models/
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

### Layer Responsibilities

- `api/routes` — HTTP requests, input validation, and service invocation.
- `schemas` — API contracts and input/output validation.
- `services` — business logic and component orchestration.
- `repositories` — access to PostgreSQL data.
- `db/models` — relational data models.
- `rag` — document loading, chunking, embeddings, retrieval, prompting, and generation.
- `integrations` — external services, including Gemini, Qdrant, and Langfuse, in accordance with the existing code separation.
- `core` — configuration, sessions, security, and shared mechanisms.
- `static` — user interface.
- `tests` — implementation and quality checks.

Do not move code between layers solely for cosmetic refactoring.

---

## 3. Key Decision: The Database Is Set Up at the Very End

The databases are currently empty, so there is no need to maintain intermediate schemas to preserve existing user records.

### Database Rules Before the Final Stage

1. You may read and edit `app/db/models/`, repositories, services, schemas, and API code.
2. You may modify models and relationships as new features are implemented.
3. You may design the required tables, fields, constraints, and foreign keys.
4. You may write tests without running them.
5. Do not create intermediate Alembic migrations.
6. Do not apply migrations or create/rebuild the database schema during development.
7. Do not start the application, open Swagger, run tests, or perform runtime checks without separate user authorization.
8. Before the final launch, consolidate all models and relationships into one consistent schema.
9. At the end, prepare a clean initial migration for the current schema instead of preserving an unnecessary history of intermediate changes.
10. Before the final stage, do not perform destructive operations on existing data or Docker volumes.

**Important:** Only database schema creation and application are deferred—not the development of functionality that uses the database.

---

## 4. Main Implementation Plan

### Stage 0. Audit and Establish the Baseline

**Priority:** Critical.  
**Status:** Completed according to the previous audit; repeat only if necessary.

#### Tasks

- Verify the repository path.
- Check the Git branch, current commit, and working tree.
- Compare the baseline with commit `522cb7f` and the results of the previous audit.
- Do not overwrite uncommitted user changes.
- Record the components already implemented and the identified issues.
- Create an implementation map using four statuses:
  - Implemented
  - Needs changes
  - Missing
  - Unverified

#### Expected Result

It is clear which components exist, which require changes, and which are missing.

Do not consider runtime behavior verified based on code inspection alone.

---

### Stage 1. Complete the Ingestion Pipeline

**Priority:** Highest. This is the foundation of the entire RAG system.

Most of the implementation already exists. Improve the existing modules rather than rebuilding the pipeline from scratch.

#### 1.1. Document Loading — `app/rag/loaders.py`

- Review the PDF and TXT loaders.
- Fix PDF text extraction while preserving page numbers.
- Maintain the relationship between the extracted text and the original document.
- Handle empty files, unreadable text, and corrupted PDFs.
- Use a consistent result format for TXT without inventing page numbers.
- Separate the original filename from the internal storage path.
- Do not add OCR.

#### 1.2. Chunking

- Review chunk size and overlap.
- Preserve the text, document identifier, and required metadata.
- Do not create empty chunks.
- Ensure that every chunk has a stable identifier.
- Preserve PDF page numbers.
- Do not create fictitious pages for TXT files.
- Account for short, long, and empty documents.

#### 1.3. Embeddings

Keep the agreed local model:

- Model: `intfloat/multilingual-e5-small`.
- Dimensions: `384`.
- Documents: `passage:` prefix.
- Queries: `query:` prefix.
- No paid embedding API.

Check how the implementation handles model loading errors, empty input, excessively long text, and invalid data. Do not replace the model without approval.

#### 1.4. Qdrant Indexing

- Verify collection creation and vector dimensionality.
- Ensure that the distance metric is consistent.
- Make repeated indexing safe and prevent accidental duplicates.
- Check the creation, updating, and deletion of points belonging to a specific document.
- Preserve all metadata required for retrieval and source attribution.
- Handle Qdrant errors.

#### 1.5. Document Statuses

Agree on a single status vocabulary before changing related contracts.

The current code uses `processing`, `completed`, and `failed`, while the original specification used `ready`.

Do not change these values automatically. After reaching an agreement:

- Ensure that status transitions are correct.
- Consider a document ready only after all required processing steps have completed successfully.
- Preserve diagnostic information when an error occurs without exposing secrets.
- Do not allow a metadata-only endpoint to create a fictitious ready document.

#### Stage Result

There is a predictable path from PDF/TXT files to indexed chunks. Each chunk retains its relationship to the original document and, where applicable, its page.

---

### Stage 2. Complete Retrieval and Qdrant Metadata

**Priority:** Highest. Depends on Stage 1.

#### 2.1. Payload Structure

Prepare a payload containing these fields:

- `workspace_id`
- `document_id`
- `chunk_id`
- `chunk_index`
- `text`
- `filename`
- `page`, where applicable

`chunk_id` must uniquely identify a chunk. Do not rely on the chunk index alone.

#### 2.2. Search Filtering

- Pass `workspace_id` to retrieval.
- Filter data on the Qdrant side.
- Support searching within a single document and a selected set of documents.
- Do not rely exclusively on filtering results after retrieval.
- Handle empty result sets correctly.
- Prevent chunks from another workspace from entering the generation context.

#### 2.3. Source Consistency

- Map Qdrant identifiers to application data.
- Account for the fact that the existence of a point does not prove that a document is ready.
- Check document existence and accessibility at the application level.
- Provide diagnostics for inconsistencies between the vector index and relational data.

#### Stage Result

Retrieval returns only authorized chunks, with sufficient metadata for generation and source verification.

---

### Stage 3. Complete RAG Generation

**Priority:** Highest. Depends on Stages 1–2.

#### 3.1. Retrieval Service

- Review the current search implementation.
- Agree on the number of chunks to retrieve and the relevance parameters.
- Preserve the identifiers and metadata of retrieved results.
- Pass source information downstream along with the text.
- Preserve result ordering and relevance where needed for diagnostics.

#### 3.2. Context Preparation

- Build the context from retrieved chunks.
- Preserve the mapping between each context fragment and its original chunk.
- Do not include unauthorized documents.
- Account for the model's context-window limit.
- Do not introduce arbitrary external information.

#### 3.3. Gemini Generation

- Review the existing prompt.
- Require answers to be based on the provided context.
- Handle insufficient context.
- Do not present unsupported claims as facts taken from the documents.
- Handle provider timeouts, errors, and rate limits.
- Verify the use of the official Google GenAI SDK.
- Verify whether `gemini-3.8-flash` is available before the final launch; do not assume its availability in advance.

#### 3.4. Structured Result

Instead of returning a single string, the service must return a consistent object containing:

- `answer`
- `insufficient_context`
- `sources`
- Internal retrieval data, if needed, for history persistence and observability.

#### Stage Result

RAG can retrieve relevant context, generate an answer, indicate when information is insufficient, and pass source information downstream without losing identifiers.

---

### Stage 4. Answer Sources and Conversation History

**Priority:** High. Depends on Stage 3.

#### 4.1. Source Structure

Create or update the source schema in `app/schemas`.

Each source must include:

- `document_id`
- `filename`
- `page`, where applicable
- `chunk_id`
- `snippet`

#### 4.2. Source Validation

- Generate sources only from chunks that were actually retrieved.
- Verify that each source is accessible within the current workspace.
- Do not allow the model to determine which document and page identifiers are considered verified.
- Do not return links to documents absent from the retrieved context.
- Separate the answer text from machine-verifiable source metadata.

#### 4.3. Chat API Contract

Update `ChatResponse` to include:

- `conversation_id`
- `question`
- `answer`
- `insufficient_context`
- `sources[]`

Ensure that the types are consistent with the project's existing schemas.

#### 4.4. Message History

- Review the `Message` model and existing services.
- Define how sources will be stored alongside the answer.
- Prepare the necessary model and contract changes without creating migrations.
- Ensure that saving the answer and its sources is logically consistent.
- Support restoring sources when conversation history is loaded again.
- Decide how deleted documents should be handled: retain a historical snapshot of the source or mark the source as unavailable without losing the answer history.

#### 4.5. History API

- Return sources when loading conversation history.
- Verify access to conversations and messages.
- Do not expose messages or sources belonging to other workspaces.

#### Stage Result

Answers contain verifiable sources. When a user reopens a conversation, they see the same answer and its sources.

---

### Stage 5. Security and Session Isolation

**Priority:** Critical. Design the security architecture before expanding the API and UI.

Full security implementation must not be postponed until the very end because security affects the contracts of all subsequent components.

#### 5.1. Session Model

- Define a mechanism for anonymous user sessions.
- Use a cryptographically random identifier.
- Transmit it through a secure cookie or an agreed equivalent.
- Define the session lifetime and behavior when a session expires.
- Do not treat a client-provided `workspace_id` as proof of ownership.
- Do not expose session IDs in logs or public responses.

#### 5.2. `app/core/security.py`

- Implement a shared mechanism for obtaining the current session.
- Implement shared access checks for workspaces, documents, and conversations.
- Use a consistent authorization mechanism across routes and services.
- Handle missing or invalid cookies safely.

#### 5.3. API Ownership Checks

Implement access checks for:

- Workspaces.
- Documents and processing statuses.
- Conversations and messages.
- Chat requests.
- Evaluation cases, runs, and results.

Verify that every object belongs to the current session rather than checking only whether its ID exists.

#### 5.4. Files and Qdrant

- Verify ownership before reading or deleting files.
- Do not accept arbitrary filesystem paths from the client.
- Protect against path traversal.
- Validate permitted file extensions and upload sizes.
- Apply workspace filters on the Qdrant side.
- Prevent deletion of data belonging to another session.

#### 5.5. General Protection

- Review CORS and cookie settings.
- Never expose secrets in the frontend.
- Set reasonable request limits.
- Account for prompt injection in uploaded documents.
- Do not send full document text to external telemetry by default.

#### Stage Result

The contracts and implementation prevent access to another user's workspaces, documents, conversations, messages, and Evaluation data through ID substitution.

---

### Stage 6. Document Selection for Each Question

**Priority:** High. Depends on retrieval, history, and the security model.

#### 6.1. API

- Add `document_ids` to the question request.
- Define behavior when the field is omitted.
- Define behavior when the list is empty.
- Validate the ID format and number of IDs.
- Verify ownership and readiness of the selected documents.

#### 6.2. Retrieval

- Pass the selected documents to the Qdrant filter.
- Do not include chunks from unselected documents in the prompt.
- Handle deleted, inaccessible, and unready documents correctly.
- Store the sources actually used in the conversation history.

#### 6.3. Default Behavior Decision

Before implementation, agree on one of the following behaviors:

- If the list is omitted, use all ready documents in the current workspace.
- If the list is omitted, require the user to explicitly select documents.

An empty list and an omitted field must not accidentally be interpreted as the same thing.

#### Stage Result

Users can restrict a question to selected documents, and retrieval and generation do not use other documents.

---

### Stage 7. Operational Reliability and Data Consistency

**Priority:** High.

#### 7.1. Uploads

- Define the order of file storage, document record creation, and indexing.
- Account for failures at every step.
- Do not leave a document with a fictitious ready status after partial indexing.
- Remove only failed-operation artifacts that can be positively identified as belonging to that operation.
- Provide compensation or a diagnosable state that supports recovery.

#### 7.2. Document Deletion

- Verify ownership.
- Define the deletion order for the file, document record, and Qdrant points.
- Handle partial failures.
- Ensure that the operation can be safely repeated.
- Do not report complete deletion if some data remains.

#### 7.3. Workspace Deletion

- Define deletion rules for related documents, conversations, messages, and Evaluation data.
- Design PostgreSQL transaction boundaries.
- Avoid performing external Qdrant and filesystem operations inside long-running database transactions unless necessary.
- Provide diagnostics for partial failures.

#### 7.4. Message Persistence

- Agree on how questions, answers, and sources are stored.
- Handle generation errors.
- Do not save a fictitious successful answer when a timeout occurs.
- Prevent partially persisted results from being left without a clear status.

#### Stage Result

Operations either complete consistently or leave a diagnosable state that can be handled safely on retry.

---

### Stage 8. Complete the Frontend

**Priority:** High. Depends on the API, sources, and security.

Work within the existing `app/static` structure without changing the architecture.

#### 8.1. Initialization

- Define how the initial application state is loaded.
- Retrieve available workspaces through the API.
- Select or create a workspace according to the agreed rules.
- Remove dependencies on an uninitialized `selectedWorkspace`.
- Display an empty application state correctly.

#### 8.2. Workspaces

- Create workspaces and view the workspace list.
- Select the current workspace.
- Delete a workspace with confirmation.
- Handle empty lists and API errors.

#### 8.3. Documents

- Upload PDF/TXT files.
- Display the document list.
- Display processing statuses and errors.
- Delete documents.
- Select documents for a question.
- Refresh the state after operations.
- Do not display a document as ready without a confirmed status from the API.

#### 8.4. Chat

- Create conversations.
- Submit questions.
- Display answers.
- Restore conversation history.
- Display insufficient-context responses.
- Handle provider errors.
- Show a loading indicator.
- Prevent duplicate submissions while a request is in progress.

#### 8.5. Sources

- Display the filename.
- Show the page number, if available.
- Show the snippet.
- Associate sources with the specific answer they support.
- Support multiple sources.
- Handle deleted or inaccessible documents.

#### 8.6. UX

- Display clear error messages.
- Distinguish between request errors, missing documents, and insufficient context.
- Do not expose stack traces or secrets in the interface.
- Perform core actions without fully reloading the page, where consistent with the existing implementation.

#### Stage Result

The primary user workflow is available through the browser without manual API requests or manually modifying application state.

---

### Stage 9. Evaluation Mode

**Priority:** High.

#### 9.1. Evaluation Model

Review the existing models and do not create duplicate entities unnecessarily.

A test case must support:

- `question`
- `reference_answer` or `required_facts`
- `expected_sources` or expected pages, optionally.

#### 9.2. API

- Create test cases.
- View, edit, and delete test cases.
- Start an Evaluation run.
- Retrieve execution status.
- Retrieve results.
- Enforce ownership checks.
- Validate selected documents and expected sources.

#### 9.3. Actual RAG Execution

- Use the same retrieval pipeline as the regular chat.
- Pass the test-case question and selected documents.
- Obtain the model's actual answer.
- Store the sources actually retrieved.
- Store the execution status and diagnostic information in case of failure.
- Do not replace actual execution with a predefined `result_text`.

#### 9.4. Metrics

Implement explainable, deterministic metrics.

**Retrieval:**

- Whether the expected sources were retrieved.
- Whether the retrieved and expected sources overlap.
- Precision/recall when sufficient ground-truth annotations are available.

**Answer:**

- Whether the required facts are covered.
- Whether formalizable key facts are present.
- Do not use simple string matching as a universal quality metric.

**Sources:**

- Whether the actual sources match the expected sources.
- Whether identifiers and page numbers are correct.
- Whether any sources appear that were not part of the retrieved context.

Do not make LLM-as-a-judge part of the mandatory foundation without separate approval.

#### 9.5. Result Storage

- Store the execution date, status, and results.
- Store the answer, actual sources, and metric values.
- Allow users to view previous runs.
- Preserve history when a test is run again.
- Handle deleted documents.

#### 9.6. Evaluation UI

- List test cases.
- Create and edit test cases.
- Select documents.
- Start an Evaluation run.
- Display execution status.
- Display results in a table.
- View answers, sources, errors, and discrepancies.

#### Stage Result

Evaluation runs the actual RAG pipeline, calculates metrics, stores the results, and displays them to the user.

---

### Stage 10. Langfuse v4 Integration

**Priority:** Medium. Must not block the core RAG functionality.

#### 10.1. Configuration

- Define environment variables.
- Add the required settings to `.env.example`.
- Do not store secrets in code.
- Support enabling and disabling the integration.
- Do not make Langfuse mandatory for local execution.

#### 10.2. SDK

- Verify compatibility with the Langfuse v4 interface.
- Use the current `get_client()` and observations APIs according to the installed version.
- Do not copy incompatible examples from older versions.
- Ensure that the core RAG pipeline does not fail when optional telemetry is unavailable.

#### 10.3. Tracing

- Create a trace for question processing.
- Trace retrieval and generation as separate steps.
- Record step durations.
- Record errors and execution status.
- Record usage and token counts, where available.
- Link related operations through a common trace.

#### 10.4. Privacy

- Do not transmit full document text by default.
- Do not send API keys, cookies, or tokens.
- Define the minimum telemetry required.
- If transmitting sensitive content becomes necessary, require a separate, explicit opt-in.
- Document the implications of enabling detailed telemetry.

#### Stage Result

Langfuse provides observability into the RAG pipeline, while the application continues to work when the integration is disabled.

---

### Stage 11. Prepare and Fix Tests Without Running Them

**Priority:** High. Executing tests remains prohibited until the final stage.

At this stage, tests may be written, edited, and statically analyzed. Do not run them without separate user authorization.

#### 11.1. Unit Tests

Prepare or update the following checks.

**Loaders:**

- Multi-page PDF.
- TXT.
- Empty and corrupted files.
- Page preservation.

**Chunking:**

- Empty, short, and long text.
- Overlap.
- Metadata preservation.

**Embeddings:**

- `passage:` and `query:` prefixes.
- Dimension count of 384.
- Invalid input.

**Retrieval:**

- Empty result sets.
- Workspace filtering.
- Selected-document filtering.
- Source metadata preservation.

**Generation:**

- Sufficient context.
- Insufficient context.
- Provider errors and timeouts.
- Current function argument signatures.

**Services and repositories:**

- Data operations.
- Operation failures.
- Repeated deletion.
- Message and source persistence.

#### 11.2. Fix Outdated Tests

The audit identified the following issues:

- `tests/unit/test_generation.py` contains expectations that do not match the current function calls.
- The workspace deletion test expects the previous behavior with status code `409`.

Compare these tests with the current contracts. Fix the tests if they are outdated; do not change correct business logic solely to satisfy outdated expectations.

#### 11.3. Integration Tests

Prepare scenarios covering:

- Workspace creation.
- Document upload and processing.
- Indexing and retrieval.
- Question answering and history persistence.
- Sources in answers and history.
- Document selection.
- Document deletion.
- Partial failure and recovery.
- Evaluation and result viewing.
- Langfuse when the integration is enabled.

#### 11.4. Security Tests

- Access to another user's workspace is denied.
- Reading and deleting another user's document are denied.
- Another user's conversation history is inaccessible.
- Another user's `document_id` cannot be used in a question.
- Another user's Evaluation cases and results are inaccessible.
- Workspace filtering cannot be bypassed by manipulating request parameters.

#### 11.5. Evaluation Tests

- Metrics are verified against known examples.
- Missing expected sources do not produce false-positive results.
- Empty retrieval results are handled correctly.
- Results can be saved and restored.
- Deleted documents are handled predictably.

#### Stage Result

Tests are prepared and match the current contracts. Actual test execution is deferred to the final stage.

---

### Stage 12. Configuration, Dependencies, and Docker

**Priority:** Medium. Must be completed before final verification.

#### 12.1. Python Version

There are currently conflicting requirements: Python 3.12 in the specification, Python 3.14.8 in the local environment, Python 3.11 in the Dockerfile, and Python 3.14+ mentioned in the README.

- Check library requirements.
- Select one supported version.
- Align the local environment, Docker, and documentation.
- Do not change the version without checking compatibility.

#### 12.2. `requirements.txt`

- Compare dependencies with actual imports.
- Add required missing packages.
- Remove only dependencies confirmed to be unused.
- Check for duplicate pytest entries.
- Check `httpx2` and NumPy usage.
- Add a compatible Langfuse SDK.
- Pin versions where necessary for reproducibility.

#### 12.3. `.env.example`

Agree on the required environment variables:

- Gemini API key.
- PostgreSQL.
- Qdrant.
- File storage.
- Embedding model.
- Generation parameters.
- Langfuse.
- Sessions and cookies.
- Upload and request limits.

Do not include real secrets.

#### 12.4. Docker and Compose

- Review `Dockerfile` and `docker-compose.yml`.
- Align the Python version.
- Configure the correct service addresses for the container network.
- Review volume configuration for file storage.
- Define when the final migration is applied.
- Ensure that a standard restart does not delete data.
- Do not use `docker compose down -v`.

#### Stage Result

The configuration is ready for the final launch, but the database is not rebuilt and runtime checks are not executed.

---

### Stage 13. Documentation and Final Static Audit

**Priority:** Must be completed before database assembly.

#### 13.1. README

Document:

- Installation and local setup.
- Environment variables.
- Starting the application and its dependencies.
- Creating a workspace and uploading documents.
- Using chat and viewing sources.
- Evaluation.
- Langfuse.
- MVP limitations.
- Applying migrations during initial database setup.

Do not claim that functionality works if it has not passed the corresponding verification.

#### 13.2. Project Consistency

- Correct outdated statements about the RAG implementation status.
- Correct the Python version information.
- Correct `AGENTS.md` if it incorrectly states that Gemini is used for embeddings.
- Check consistency between configuration, imports, schemas, API contracts, and instructions.
- Ensure that new features have not violated the agreed architecture.

#### 13.3. Final Static Audit

Before creating the database, verify that:

- All required features are represented in the implementation.
- Models represent all required entities and fields.
- Relationships and foreign keys are designed consistently.
- Repositories and services use consistent fields and contracts.
- The API and frontend are aligned.
- Tests match the current implementation.
- Configuration contains no contradictions.

#### Stage Result

The main implementation is complete, and the project is ready for final database schema alignment.

---

### Stage 14. Final Database Assembly, Launch, and MVP Acceptance

**Final stage.** This stage may begin only after the main implementation is complete and the user has separately authorized runtime checks.

This stage combines final PostgreSQL setup, migrations, environment preparation, application launch, and all tests.

#### 14.1. Final PostgreSQL Schema

- Review all models in `app/db/models/`.
- Review relationships between workspaces, documents, conversations, messages, Evaluation cases, and results.
- Align fields, types, constraints, indexes, and foreign keys.
- Check `documents.file_path` and other previously identified discrepancies.
- Verify that models are imported into Alembic metadata.
- Create one clean initial migration representing the final schema.
- Do not carry unnecessary intermediate migrations into the new schema history.
- Statically review `upgrade()` and `downgrade()`.
- Preserve necessary user code changes and do not perform destructive data operations without separate approval.

#### 14.2. Final Environment Setup

After the user grants permission:

- Prepare a consistent test environment.
- Create or rebuild an empty database according to the agreed plan.
- Apply the final migration.
- Verify PostgreSQL and Qdrant availability.
- Verify the Gemini configuration.
- Test Langfuse separately if necessary.
- Do not delete Docker volumes without explicit approval.

#### 14.3. Main Workflow Verification

- Create a workspace.
- Upload a PDF.
- Upload a TXT file.
- Verify that processing completes.
- Verify chunks and embeddings in Qdrant.
- Ask a question whose answer is present in the documents.
- Verify the answer and its sources.
- Ask a question whose answer is absent from the documents.
- Verify `insufficient_context`.
- Restrict retrieval to a selected document.
- Verify that other documents do not enter the context.
- Open the conversation history and verify that sources have been preserved.
- Delete a document and verify data consistency.

#### 14.4. Isolation Verification

- Create two independent sessions.
- Verify that neither session can access the other's data.
- Test ID substitution for workspaces, documents, conversations, and Evaluation objects.
- Verify isolation at the API, PostgreSQL, and Qdrant levels.

#### 14.5. Evaluation Verification

- Create a test case.
- Run the actual RAG pipeline.
- Verify the calculated metrics.
- Verify the actual sources.
- Save the result and open it again.

#### 14.6. Langfuse Verification

- Enable the integration.
- Verify the trace and processing steps.
- Verify diagnostic events and available token information.
- Ensure that secrets and full document text are not transmitted by default.
- Disable the integration and verify that the main workflow still works.

#### 14.7. Test Execution

Only at this stage, run:

1. Unit tests.
2. Integration tests.
3. Security tests.
4. Evaluation tests.

Fix any errors and repeat the relevant checks. Do not replace implementation fixes with disabling mandatory checks.

#### 14.8. Final Acceptance

- Compare actual behavior with the README.
- Verify a clean startup using the documented instructions.
- Record the test results.
- Prepare a list of completed requirements.
- List known limitations and unresolved issues separately.

#### Completion Criteria

The MVP is considered ready after the main workflows, source correctness, data isolation, Evaluation functionality, PostgreSQL/Qdrant consistency, successful startup, and all mandatory tests have been verified.

---

## 5. Condensed Execution Order

| # | Stage | Main Goal |
|---:|---|---|
| 0 | Audit | Establish the baseline |
| 1 | Ingestion pipeline | Reliable PDF/TXT processing |
| 2 | Retrieval and Qdrant | Correct search with metadata |
| 3 | RAG generation | Answers and insufficient-context handling |
| 4 | Sources and history | Verifiable sources in answers |
| 5 | Security | Session and object isolation |
| 6 | Document selection | Controlled retrieval |
| 7 | Operational reliability | Consistency between files and the index |
| 8 | Frontend | Complete user workflow |
| 9 | Evaluation | Actual RAG quality assessment |
| 10 | Langfuse v4 | Observability |
| 11 | Test preparation | Tests prepared and reviewed statically |
| 12 | Configuration and Docker | Reproducible environment |
| 13 | Documentation and audit | Preparation for final assembly |
| 14 | Database, launch, and testing | Final MVP acceptance |

---

## 6. Working Rules for DeepSeek Harness

Use a short cycle for every task:

1. **Audit:** Read the related files and describe the current implementation.
2. **Alignment:** Define the expected behavior and acceptance criteria.
3. **Small change:** Edit only the necessary files.
4. **Agent report:** List changed files, results, and limitations.
5. **Static verification:** Compare the code against the requirements and architecture.
6. **Acceptance:** Accept the result before moving to the next task.

Do not assign the entire project to the agent at once. Do not allow it to change the architecture without notice. Do not consider a task complete solely because the agent reports success.

### Restrictions Before the Final Stage

The following actions are prohibited without separate user authorization:

- Starting the application or Swagger.
- Running tests.
- Applying migrations.
- Creating or rebuilding the database schema.
- Performing runtime checks.
- Deleting Docker volumes.

It is permitted to inspect files, modify code, align contracts, design the final schema, and write tests without executing them.

---

## 7. Decisions to Agree On Before Dependent Tasks

1. The status of a ready document: `completed` or `ready`.
2. The available Gemini model and its final name.
3. Chat behavior when no documents are selected.
4. The policy for retaining sources after document deletion.
5. Session lifetime and cookie settings.
6. Evaluation ground-truth format and metric set.
7. Langfuse privacy policy.
8. Supported Python version.
9. Final PostgreSQL fields, relationships, and constraints before database assembly.

These decisions do not all need to be made at once. Each must be resolved before implementing the functionality that depends on it.

---

## Final Completion Criteria

DocuChat MVP v1 is ready when a user can safely create a workspace, upload PDF/TXT documents, ask a question about selected documents, receive an answer with verifiable sources, restore conversation history, delete a document, run Evaluation, and view the results.

The project must be reproducibly installable, use PostgreSQL and Qdrant correctly, enforce session isolation, and pass all mandatory tests.

**Core principle:** First implement the functionality and align all contracts. Then assemble the final database once, and only afterward start the application and perform final verification. No mandatory MVP component may be excluded merely to speed up development.
