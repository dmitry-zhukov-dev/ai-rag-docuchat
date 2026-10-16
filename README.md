# DocuChat

RAG application for chatting with documents uploaded by the user.

## Current status

The initial FastAPI skeleton is in place. The `/health` endpoint is separated
into its own router. Application metadata is kept in `app/core/config.py`.

## Run locally

From the project root, create and activate a virtual environment, then install
the current minimal dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` for the health check and
`http://127.0.0.1:8000/docs` for the interactive API documentation.

## Development approach

Implement features incrementally. The application will answer only from
documents uploaded by the user; no built-in document corpus is planned.
