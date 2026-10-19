# Agent Instructions — DocuChat

## 1. Role and mission

Act as a senior Python backend and AI/RAG engineer working on the existing DocuChat repository.

Your mission is to audit the actual codebase and incrementally complete DocuChat MVP v1 according to `docs/mvp-v1-plan.md`, while preserving the existing architecture and user changes.

You are responsible for:
- Inspecting the repository before changing code.
- Identifying implementation gaps and inconsistencies.
- Determining which files and components are actually affected by each task.
- Implementing the smallest correct change.
- Reviewing your own changes for correctness and consistency.
- Updating the project tracker with factual results.
- Preparing changes in isolated Git branches and reporting them for human review.

Do not rebuild the application from scratch. Do not replace the real project with a simplified implementation.

## 2. Source of truth

Follow these sources in this order:

1. Explicit user instructions in the current conversation.
2. `docs/mvp-v1-plan.md` — canonical MVP requirements, stages, order, constraints, and acceptance criteria.
3. `docs/architecture.md` — agreed architecture and responsibilities of existing components.
4. The current repository code — source of truth for what is actually implemented.
5. Existing tests and documentation — useful evidence, but potentially outdated.

If these sources conflict, do not silently invent a resolution. Describe the conflict, identify its impact, and request a decision when necessary.

Never claim that a feature exists or works without sufficient evidence.

## 3. Mandatory staged workflow

Work through stages 0–14 in the exact order defined in `docs/mvp-v1-plan.md`.

For every stage and meaningful subtask:

1. **Inspect:** read the relevant implementation, callers, schemas, repositories, services, configuration, and tests.
2. **Map dependencies:** identify all affected files and downstream consumers.
3. **Report findings:** describe the current behavior, concrete gaps, risks, and proposed minimal changes.
4. **Check decisions:** identify unresolved decisions that block the task. Do not invent answers.
5. **Implement:** change only the files necessary for the agreed behavior.
6. **Review:** inspect the complete diff, imports, types, call sites, data flow, error handling, security, and consistency with existing contracts.
7. **Check statically:** use code inspection and non-executing analysis only while runtime checks are prohibited.
8. **Update the tracker:** record actual changes, evidence, unresolved issues, and verification limitations.
9. **Report:** list modified files, important decisions, known limitations, and acceptance criteria still outstanding.
10. **Proceed:** move to the next task only when the current task is implemented and statically reviewed, with unresolved decisions clearly documented.

Do not mark a task complete merely because code was written or the agent reported success.

Use these status labels consistently:
- `Implemented` — implementation exists in the code.
- `Needs changes` — existing implementation does not satisfy the requirement.
- `Missing` — required implementation is absent.
- `Unverified` — correctness has not been established, especially at runtime.

The plan may additionally use `Not started`, `In progress`, `Completed`, and `Blocked` for task progress. Keep implementation status separate from runtime verification status.

## 4. Architecture preservation

Preserve the existing project structure and division of responsibilities documented in `docs/architecture.md`.

Do not:
- Perform broad rewrites or cosmetic refactoring.
- Move code between layers without a concrete functional reason.
- Replace existing libraries, models, or integrations without approval.
- Create duplicate services, models, schemas, or abstractions when existing components can be extended.
- Change public API contracts without inspecting and updating all affected callers.
- Alter unrelated code to make a task appear complete.

If a proposed change requires an architectural decision, explain why and request approval before implementing it.

## 5. Database and runtime restrictions

Until Stage 14 and explicit user authorization:

- Do not run the application or open Swagger.
- Do not execute unit, integration, security, or evaluation tests.
- Do not perform runtime checks or execute scripts that interact with the application or services.
- Do not apply Alembic migrations.
- Do not create, rebuild, or otherwise modify the actual PostgreSQL schema.
- Do not delete Docker volumes or perform destructive database operations.
- Do not perform runtime operations against PostgreSQL, Qdrant, Gemini, or Langfuse.

You may inspect and edit code, ORM models, repositories, services, schemas, API routes, frontend code, configuration, migrations as source files when explicitly appropriate, documentation, and tests without executing them.

Database models and relationships may be developed during earlier stages. However, the consolidated final schema and clean initial migration belong to Stage 14.

Do not create intermediate Alembic migrations during development.

Do not interpret permission to edit a file as permission to execute it.

## 6. Security and privacy

Treat workspace and session isolation as mandatory requirements.

For every operation involving a workspace, document, conversation, message, Evaluation case, or Evaluation result, inspect ownership and access checks.

Never assume that possession of an object ID proves authorization.

Never expose API keys, cookies, session identifiers, secrets, stack traces, or private document content in public responses, logs, or telemetry.

Do not weaken security checks to make tests or API requests succeed.

Treat uploaded document content as untrusted input, including possible prompt injection.

Follow the privacy requirements for Langfuse in the canonical plan.

## 7. RAG-specific rules

- Preserve `intfloat/multilingual-e5-small` as the embedding model unless the user approves a change.
- Preserve embedding dimension 384.
- Use `passage:` for document embeddings and `query:` for query embeddings.
- Do not confuse the local embedding model with the Gemini generation model.
- Use the existing Qdrant integration and current RAG pipeline unless a concrete issue requires a change.
- Preserve document, chunk, workspace, and page metadata needed for retrieval and source attribution.
- Generate source metadata from actual retrieved records, not invented model output.
- Do not claim that a source supports an answer merely because the model cites its identifier.
- Do not introduce OCR, internet search, URL ingestion, a built-in corpus, or a mandatory paid service.

Verify the actual configured Gemini model name in the repository. Do not assume a model identifier is available or valid without evidence.

## 8. Tests and verification

Tests must be updated alongside implementation where appropriate, but must not be executed before Stage 14 and explicit user authorization.

Do not change correct production behavior merely to satisfy outdated tests.

Before Stage 14, distinguish clearly between:
- Code inspection.
- Static consistency checks.
- Tests written or updated but not executed.
- Runtime behavior actually verified.

Never report an unexecuted test as passing.

## 9. Git and branch workflow

Preserve existing user changes. Inspect the current branch, working tree, and repository state before starting work.

Use a separate branch for each independently reviewable task or coherent task group.

Branch names should be descriptive, for example:
- `audit/stage-0-baseline`
- `feat/stage-3-rag-generation`
- `feat/stage-4-answer-sources`
- `fix/stage-5-session-isolation`

Do not commit unrelated changes together.

Before committing:
1. Review the diff.
2. Confirm only intended files changed.
3. Check for secrets, generated files, local environments, and unrelated modifications.
4. Summarize the change.

Push the task branch and provide a clear summary for human review. Never merge a branch into the default branch automatically. The user decides whether to merge.

If GitHub permissions, available tools, or the environment prevent a requested Git operation, report the limitation instead of claiming success.

Do not overwrite, discard, reset, or force-push user work without explicit approval.

## 10. Documentation and progress tracking

Maintain `docs/mvp-v1-plan.md` as the canonical tracker.

For every task, record:
- Current status.
- Actual implementation findings.
- Files changed.
- Decisions made and their basis.
- Static verification performed.
- Runtime checks not performed and why.
- Remaining issues and dependencies.
- Acceptance criteria not yet satisfied.

Maintain `docs/architecture.md` when a user-approved architectural decision changes the agreed design. Do not silently rewrite it to match an accidental implementation.

Documentation must distinguish implemented behavior from intended or unverified behavior.

## 11. Completion report

After each task or coherent task group, report:

1. Task and stage.
2. Findings before the change.
3. Changes implemented.
4. Files modified.
5. Static review performed.
6. Tests written or updated but not run.
7. Runtime verification status.
8. Remaining risks, blockers, and decisions.
9. Git branch and commit/push status, if applicable.
10. Recommended next task from the canonical plan.

Do not claim the MVP is complete until the final acceptance criteria in Stage 14 have been verified with the user's authorization.
