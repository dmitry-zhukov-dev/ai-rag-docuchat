# Anonymous DocuChat — implementation report

Date: 2026-10-20. Status: **Implemented in source; runtime unverified. Migration not applied.**

## Original causes and inspection

See `anonymous-chat-inspection.md` for the inspected files and original request flow. The main causes were DOM `document` shadowing during nonempty-list rendering, unconditional session replacement combined with JavaScript attempting to read an HttpOnly cookie, manual-only workspace/chat setup, and unconditional document creation on every upload. Documents had no content hash or chat association. Existing stable Qdrant IDs could not deduplicate newly allocated document IDs.

## Approved schema strategy

Only the approved two columns and their required constraints were added in source:

- Nullable `documents.conversation_id` and `documents.file_hash` (64-character SHA-256).
- `uq_documents_conversation_hash` on `(conversation_id, file_hash)`. PostgreSQL's default NULLS DISTINCT behavior allows multiple unchanged legacy rows with null values; populated pairs must be unique. No partial index or separate owner column is necessary. A chat's owner is derived through its workspace and session.
- `ck_documents_scope_hash` requires both values null, or both populated with a 64-character hash. Mixed null values cannot bypass deduplication.
- Composite FK `(conversation_id, workspace_id)` → `(conversations.id, conversations.workspace_id)` enforces that a scoped document belongs to the same workspace as its chat. PostgreSQL requires the referenced composite unique key even though conversation ID already uniquely identifies a row; `uq_conversations_id_workspace` supplies it. Default MATCH SIMPLE leaves legacy rows untouched when conversation_id is null.
- Conversation deletion is restricted while scoped documents exist. No cascading vector/data deletion was introduced. Automatic migration downgrade deliberately refuses to remove privacy scope after new uploads.

This strategy was checked against source definitions and PostgreSQL semantics only; no live constraint or locking checks were run. No additional columns/tables are needed. No backfill, legacy chat assignment, duplicate removal, data reset, or initial-migration rewrite was performed.

**Deployment gate:** the updated ORM requires these columns. Do not deploy/start this version against the old schema. Applying `d8e2f6a1b903` needs separate authorization and deployment review; it has not been applied.

## Identity and context

POST `/api/v1/sessions` now resolves an existing active request cookie and returns 200 without rotating it or extending its browser expiry beyond the database expiry. Missing/invalid/expired cookies create a new anonymous session (201). Expiration lookup no longer tries to delete sessions that own workspaces. Frontend always asks the server; it never reads the cookie or exposes it in state. Failed authenticated mutations are not automatically replayed under a new identity.

Existing random UUID bearer IDs and database storage are intentionally retained to preserve the approved security/cookie model and legacy access. Tokens remain raw database session IDs, **not newly hashed**. Cookie defaults remain HttpOnly, SameSite=Lax, 30-day lifetime; set SESSION_COOKIE_SECURE=true for HTTPS production. Existing CORS configuration is unchanged; the UI uses same-origin credentialed relative requests. No cross-origin deployment was verified.

POST `/api/v1/sessions/context` resolves the authorized default context while locking the session row. It chooses the lowest-ID owned workspace and its lowest-ID conversation, or creates missing records in one transaction. This does not assign any legacy document to a chat. No schema default-pointer column, localStorage bearer token, or multi-chat sidebar was introduced. The default IDs are deterministically restored from the server.

## Upload, concurrency and retry

The existing workspace upload endpoint now **requires `conversation_id` as a query parameter** and authorizes both objects and their relationship. It hashes stored upload bytes exactly once. A short PostgreSQL transaction locks the conversation row, finds/creates the `(conversation_id, file_hash)` record, and commits processing before ingestion. Other workers return the existing record's completed/processing/failed state instead of embedding again. The database unique key is a backstop; all byte uploads go through the existing document repository's claim method. Different conversations have separate claims, file storage and document/vector IDs.

Response retains DocumentResponse fields and adds `disposition`: accepted, already_exists, processing, failed, or retried. New/retried ingestion returns 201; reused records return 200. A failed record is not retried implicitly: `retry=true` is required and claims the failed → processing transition under the same lock. The UI asks for confirmation after identifying an existing failed document. Same-name changed bytes create a distinct record; renamed identical bytes reuse the original metadata.

The unchanged synchronous ingestion pipeline is offloaded via Starlette's existing threadpool helper so document-status requests can be served while ingestion runs. No task queue, new dependency or RAG rewrite was introduced. Status PATCH is now rejected for public callers, preventing clients from bypassing the processing claim protocol; tests that need ready legacy fixtures use server-side setup instead.

## PostgreSQL/Qdrant consistency and isolation

Existing stable UUID5 chunk IDs remain unchanged. Reused completed/processing uploads do not call ingestion. Explicit failed retries delete only that document's points before reindexing, preventing stale tail chunks after a partial attempt. Existing targeted failure compensation remains. This is not a distributed transaction: PostgreSQL readiness is the gate for retrieval. No vectors or stored files were changed during this coding session.

Chat retrieval now includes completed documents assigned to that chat plus approved legacy documents with no chat association. Explicit selected document IDs receive the same filter. Workspace ownership, Qdrant workspace filtering, authorized document IDs and source snapshots are preserved. New uploads in another chat cannot enter this chat's RAG context. Owner-authorized workspace listing and evaluation tooling remain workspace-level administrative operations; evaluations were not removed from the backend.

Deletion uses the same conversation lock as claims and refuses processing scoped documents. Chat deletion requires scoped document cleanup first; workspace cleanup stops instead of deleting chats if documents remain. Existing explicit deletion workflows remain available; no automatic deletion of old data was added.

## Frontend and errors

The existing static frontend and citation rendering are retained, with manual workspace/chat and evaluation panels removed from the normal page. The page supports native keyboard-operable file selection and page drop, configured size validation, single in-flight upload, real status polling, deletion and a bottom composer. It restores all paginated history/documents. Composer is disabled while an upload or visible document is processing and requires at least one completed document.

DOM rows use `doc`, not `document`. Upload responses are consumed immediately; fetch/render refresh errors have their own non-destructive warning and do not report a successful upload as failed. Ambiguous upload/network failures prompt status refresh and never automatically retry ingestion. Source rendering is reused from the original code. Evaluation services, routes, scripts and test coverage remain.

## Files changed

| Files | Change |
|---|---|
| `app/api/routes/sessions.py`, `app/core/security.py` | Cookie reuse, safe expiration lookup, default context endpoint. |
| `app/db/models/document.py`, `app/db/models/conversation.py` | Approved columns and matching constraints. |
| `migrations/versions/d8e2f6a1b903_chat_document_scope.py` | Additive migration source only; no backfill; unsafe downgrade refused. |
| `app/repositories/document.py` | Locked upload claims, explicit retry, scoped document listing, deterministic pagination. |
| `app/services/document.py` | Claim delegation, scoped listing, processing/deletion serialization. |
| `app/api/routes/document.py`, `app/schemas/document.py` | Authorized chat uploads, hashing, dispositions, threadpool ingestion, explicit retry, server-owned indexing state. |
| `app/services/chat.py` | Chat-plus-legacy filtering for default and explicit document selections. |
| `app/services/conversation.py`, `app/api/routes/conversation.py` | Serialized default context, safe scoped-chat deletion conflict. |
| `app/services/workspace.py` | Stop parent cleanup when documents remain or a chat has a concurrent scoped upload. |
| `app/static/index.html`, `app/static/js/app.js`, `app/static/css/style.css` | Simple automatic upload/chat flow, status, restoration, separate refresh errors; existing source renderer reused. |
| `tests/api/test_sessions.py` | New-cookie and cookie/context reuse regression tests; unauthenticated client fixture correction. |
| `tests/api/test_documents.py`, `tests/integration/test_documents_api.py` | Required upload chat IDs and server-owned indexing state contract. |
| `tests/conftest.py`, `tests/integration/test_chat_api.py`, `tests/integration/test_evaluations_api.py` | Server-side readiness fixture instead of public status PATCH. |
| `tests/integration/test_chat_upload_scope.py` | Duplicates/renames/versions, chat isolation, failed retry, processing reuse, foreign identity rejection, legacy sharing; mocked external operations. |
| `docs/mvp-v1-plan.md`, `docs/anonymous-chat-inspection.md`, this report | Factual progress, findings, decisions and verification limits. |

## Known limitations and remaining checks

- Application, test suites, PostgreSQL queries/locks/constraints, migrations and Qdrant were **not run**. SQLite regression tests do not establish PostgreSQL locking behavior; simultaneous multi-worker uploads/default-context initialization still require a dedicated PostgreSQL verification.
- A process crash after committing processing can leave a stuck processing document. Automatic timeout retry would risk concurrent ingestion, so no guessing/reclaim mechanism was added. Recovery requires confirming no live worker before an explicit reviewed status repair; no new lease/worker column was added.
- A first-ever simultaneous visit in separate tabs with no cookie may create separate identities before either cookie is installed. Existing-cookie context requests are serialized. Cookie loss/expiry cannot recover the former identity automatically.
- Legacy documents intentionally remain workspace-shared and unhashed. Uploading legacy content creates a new scoped document; it is not compared to, adopted from, or deduplicated against legacy records.
- The UI restores one deterministic default, not an arbitrary formerly selected legacy chat. Other historical chats are preserved through existing authorized APIs.
- Existing API metadata-only documents still have null scope/hash and no ingestion; clients cannot mark them ready. Existing internal developer services remain trusted.
- Existing generation history context still uses its prior 100-message limit, though the UI paginates history. Existing generation/provider behaviors were not redesigned.
- PostgreSQL and Qdrant are not atomic. Unknown completion after a database/network failure may need operator reconciliation. Processing is deliberately conservative rather than silently launching a second job.

## Static checks actually performed

- Read relevant models, routes, repositories, services, schemas and callers; reviewed upload/status/deletion, ownership and retrieval scope paths.
- Python AST parsing of application, tests and migration source (no module imports or application execution).
- `node --check app/static/js/app.js` (syntax only).
- `git diff --check` and source diff inspection.
- No new dependencies, token responses/logs, schema application, backfill, broad Qdrant deletion or pipeline parameter changes introduced.

These checks are not runtime verification or passing test claims.

## Manual verification after separate authorization

1. Apply the reviewed additive migration in an approved environment; inspect legacy null rows and populated-pair uniqueness/composite FK rejection without changing old records.
2. Open/reload/restart browser: stable cookie, default IDs, history and status; check HttpOnly/SameSite/Secure deployment settings. Second browser cannot use foreign object IDs.
3. Upload PDF/TXT through picker and drop; invalid/empty/oversized inputs rejected. Check ready status, question, answer and source metadata.
4. Repeat same content under same/different names; confirm one record and one ingestion. Changed bytes under same name remain distinct.
5. Run simultaneous identical uploads using independent PostgreSQL connections/workers with ingestion held open: one processing record, one ingestion; duplicates return processing. Repeat with simultaneous failed retries and default-context requests.
6. Same bytes in another chat/browser produce independent records; chat retrieval excludes foreign-chat scoped documents but includes approved legacy workspace documents.
7. Induce indexing/refresh failures: explicit retry only, successful upload survives refresh failure, cleanup stays document-targeted, no extra chunks. Reload during processing.
8. Delete through the supported workflow; processing deletion is rejected and vectors for unrelated documents remain. Check public UI has no workspace/chat creation or evaluation forms.
