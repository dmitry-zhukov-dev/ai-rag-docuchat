
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".txt", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def save_uploaded_file(file: UploadFile) -> Path:
    """Validate and save an uploaded TXT or PDF file."""
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only TXT and PDF files are supported.")

    content = await file.read()

    if not content:
        raise ValueError("Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 10 MB size limit.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    saved_path = UPLOAD_DIR / f"{uuid4()}{extension}"
    saved_path.write_bytes(content)

    return saved_path
