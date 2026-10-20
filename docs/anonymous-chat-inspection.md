# Anonymous chat and document deduplication — inspection

Date: 2026-10-20. TODO 0: static inspection complete. This records the original pre-implementation findings and approval request. The user subsequently approved the additive fields/constraints and temporary legacy sharing; see `anonymous-chat-implementation.md` for implementation and remaining limitations. Runtime behavior remains unverified.

## Files inspected

- `app/static/index.html`, `app/static/js/app.js`, `app/static/css/style.css`: single-page UI, in-memory state, fetch calls, rendering, manual workflow and evaluation controls.
- `app/main.py`, `app/api/deps.py`, `app/core/config.py`, `app/core/security.py`: routing, static hosting, credentialed CORS, cookie settings and ownership helpers.
- `app/api/routes/{sessions,workspace,document,conversation,chat,evaluations}.py`: relevant API operations (evaluation route inspection was partial).
- `app/db/models/{session,workspace,document,conversation,message,evaluation}.py`, associated repositories/services and API schemas: relationships, persistence, status and history.
- `app/services/file_storage.py`, `app/rag/{ingestion,loaders,chunking,retrieval,generation}.py`, `app/integrations/{qdrant,embeddings}.py`: storage and RAG flow.
- `migrations/versions/c4f1a2b3d4e5_initial_schema.py`, migration configuration: declared schema/indexes, not the live database.
- Session/document API tests, document integration tests and `tests/conftest.py`: existing contracts and fixtures; read only.
- `AGENTS.md`, `docs/architecture.md`, `docs/mvp-v1-plan.md`: project constraints.

## Existing request/data flow

1. Browser initialization checks `document.cookie` for a cookie configured HttpOnly. JavaScript cannot see this cookie, so it calls POST `/api/v1/sessions` on reload. That endpoint unconditionally creates a new session rather than reusing the request cookie.
2. Browser lists session-owned workspaces. Workspace selection, file selection, Upload and New Chat are explicit UI handlers; no default context initialization exists. Selection is only in memory.
3. Upload POST `/api/v1/workspaces/{id}/documents/upload` authorizes workspace ownership, validates PDF/TXT (10 MB default), writes a randomly named file, commits a new document, runs ingestion synchronously, then commits completed status. Failed ingestion attempts targeted vector/file cleanup and leaves a failed record.
4. On successful POST, the frontend discards its response body and calls the document-list GET. The GET returns a list of DocumentResponse records. `loadDocuments()` wraps both fetching and rendering in the same catch.
5. Chat resolves the conversation's workspace, selects completed documents from that workspace, persists the question, retrieves/generates, then persists the answer and source snapshots. History is ordered; existing calls load at most 100 messages.
6. Session owns workspaces; workspace owns documents and conversations; conversation owns messages. There is no document-to-conversation relationship.

## Confirmed code defects and limitations

- **Misleading document-load error:** `renderDocuments()` uses `for (const document of state.documents)` and then calls `document.createElement('input')`. Here `document` is an API record, not the browser DOM. A nonempty list throws a TypeError; the enclosing catch reports `Failed to load documents` even if GET and upload succeeded. Evaluation document rendering repeats this shadowing defect. This failure path is established statically; no actual network response was observed.
- **Identity replaced on reload:** HttpOnly cookie detection in JavaScript plus unconditional session creation changes identity on reload, making previous data inaccessible to the new identity. Existing records are not necessarily lost.
- **Duplicate processing:** each upload creates a new file and database document. No SHA-256 field, duplicate lookup or uniqueness constraint exists. Qdrant uses stable UUID5 point IDs based on document ID and chunk index, but a fresh document ID on each upload means fresh vectors and repeated embedding work.
- **Chat scope absent:** multiple conversations in one workspace currently share its ready document pool. Workspace-level deduplication would not satisfy owner + chat + content uniqueness.
- **Other risks to address:** public document PATCH accepts indexing_status, allowing clients to fabricate readiness; expiration resolution attempts to delete a session with owned workspaces; concurrent context creation needs serialization; interrupted synchronous ingestion may leave processing records. These are findings, not fixed behavior.

## Minimal proposed implementation (not yet implemented)

- Reuse anonymous sessions and all ownership helpers. Make session initialization idempotent on the server; stop inspecting HttpOnly cookies in JavaScript. Introduce random bearer tokens with hashed lookup while preserving existing identities through an explicit compatibility strategy. Existing 64-character session key can hold SHA-256, but raw legacy IDs and hashed keys must never be interchangeable bearer credentials.
- Obtain/create one default workspace/chat under a database lock on the owning session; restore it server-side rather than trusting client IDs. Keep existing repositories/services, adjusting transaction boundaries where needed.
- Simplify the existing static page and handlers: immediate picker/drop upload, readiness-gated composer, status polling, history and existing citation rendering. Remove public evaluation controls, not backend evaluation infrastructure.
- Consume successful upload metadata immediately. Separate upload, refresh and rendering failures; never automatically retry uploads after an ambiguous network failure.
- Calculate SHA-256 once, claim a chat-scoped document with database uniqueness, and use transactional status transitions to permit only one ingestion attempt at a time. Return existing completed/processing state; explicit controlled retry for failed records.
- Retain Qdrant's stable IDs. Retry must remove only that document's previous points before reindexing to avoid stale trailing chunks. Only completed, authorized chat document IDs may enter retrieval. Keep existing loaders, embedding model, chunking, prompts and source snapshots.

## Approval required: schema and legacy data

Recommended additive schema change:

1. Add nullable `documents.conversation_id` referencing conversations, initially nullable for legacy records.
2. Add nullable `documents.file_hash` (64-character SHA-256 hex), initially nullable for legacy records.
3. Add uniqueness on `(conversation_id, file_hash)` for scoped/hashed records. Conversation ownership is derived through its workspace and session, so repeating owner_id is unnecessary. Enforce document/conversation workspace consistency in the service and preferably a composite database foreign key with its required referenced unique key.

New uploads must supply both fields. This represents independent documents per chat without adding a second document model or association table. Prepare a new additive migration only after approval; do not rewrite the existing initial migration or reset the database. Applying any migration remains separately prohibited.

**Legacy decision:** old documents have no recoverable chat association in the schema, and workspaces can have multiple chats. Do not guess, clone vectors, re-embed or delete duplicates. Proposed default is to preserve legacy workspace-scoped documents untouched, choose an existing context deterministically for the simple UI, and preserve legacy retrieval behavior until an explicit adoption/backfill policy is approved. That compatibility mode does not provide strict chat isolation for legacy workspace-shared documents. Alternative: explicitly assign legacy documents to a chosen chat per workspace, with approved handling of other historical chats. Hash backfill requires readable original files; missing files must remain explicitly unresolved. Existing duplicate records must not be silently deleted to satisfy uniqueness.

## Changes and checks

Only this inspection report and a tracker note were added. No application code, schemas, migrations or tests changed. Static call-path and schema comparison performed; no full endpoint security certification claimed. No application, tests, DB queries, migration commands or Qdrant operations executed. No runtime behavior verified.

## Manual verification checklist for after implementation and authorization

- Reload/restart browser: same identity, default context, history and document status.
- Separate browser: foreign workspace/chat/document/history IDs rejected.
- Picker/drop PDF and TXT; unsupported, empty and oversized input rejected.
- Identical bytes with same/different filename: same document, no extra embedding/vector work.
- Same filename with changed bytes: distinct document; different chats/users remain independent.
- Concurrent identical uploads: one record and one active ingestion; processing response reused.
- Failed indexing: controlled retry; no duplicate or stale vectors.
- Successful upload plus failed refresh: retain success, show non-destructive warning.
- Reload during processing, question readiness, correct sources/history, targeted document deletion.
- No evaluation/workspace/manual-chat controls in normal UI.
