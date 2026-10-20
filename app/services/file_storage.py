from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings

UPLOAD_DIR = Path(settings.upload_dir)
MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024
ALLOWED_EXTENSIONS = {
    extension.strip().lower()
    for extension in settings.allowed_extensions.split(",")
    if extension.strip()
}


async def save_uploaded_file(file: UploadFile) -> Path:
    """Validate and save an uploaded TXT or PDF file."""
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only TXT and PDF files are supported.")

    content = await file.read()

    if not content:
        raise ValueError("Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"File exceeds the {settings.max_file_size_mb}"
            " MB size limit."
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    saved_path = UPLOAD_DIR / f"{uuid4()}{extension}"
    saved_path.write_bytes(content)

    return saved_path
