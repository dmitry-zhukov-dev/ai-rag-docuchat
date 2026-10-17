# DocuChat — Agent Instructions

## Project goal

Build DocuChat, a modular RAG application that answers questions using only documents uploaded by the user.

No built-in document corpus or preloaded knowledge base.

## Architecture

- FastAPI — HTTP API.
- PostgreSQL + SQLAlchemy — application data and conversation history.
- Qdrant — vector search.
- Gemini API — generation and embeddings.
- Plain HTML, CSS and JavaScript — frontend.
- Pytest — automated tests.
- Docker — reproducible local deployment.

Follow the existing project structure. Do not introduce microservices, Redis, or additional infrastructure without approval.

## Development rules

1. Work on one small, explicitly defined task at a time.
2. Inspect existing code before proposing or making changes.
3. Do not rewrite the whole project.
4. Do not implement future roadmap stages without approval.
5. Do not create placeholder modules or unused abstractions without a concrete need.
6. Keep dependencies minimal and explain every new dependency.
7. Never hardcode secrets. Keep `.env` out of Git and update `.env.example` when configuration changes.
8. Do not introduce paid services or require paid API access without approval.
9. Preserve existing working behavior unless the task explicitly changes it.
10. Run relevant tests and report their actual results. Never claim a test passed if it was not run.

## Workflow

For every task:

1. Inspect the relevant files.
2. Describe the proposed changes and acceptance criteria.
3. Wait for approval before editing files.
4. Implement only the approved scope.
5. Run relevant checks.
6. Summarize changed files, decisions, test results, and remaining issues.

If a requirement is ambiguous, ask before making an architectural decision.

## Completion criteria

A task is complete only when its acceptance criteria are met, the changes are reviewed, and test results are reported.