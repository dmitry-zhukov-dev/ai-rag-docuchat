# DocuChat

RAG application for chatting with documents uploaded by the user.

## Current status

The initial FastAPI skeleton is in place, including:
- PostgreSQL configuration via SQLAlchemy and Alembic.
- REST API for Workspaces, Documents, Conversations, and Messages.
- Integration tests using `pytest` and `httpx`.

**Note: The RAG (Retrieval-Augmented Generation) pipeline is not yet implemented.**

## Prerequisites

- Python 3.14+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- Qdrant (via Docker)

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
4. Set up environment variables (see `.env.example`).
5. Start infrastructure:
   ```bash
   docker compose up -d
   ```
6. Run database migrations:
   ```bash
   alembic upgrade head
   ```
7. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running tests

Run the test suite from the project root:
```bash
python -m pytest
```
