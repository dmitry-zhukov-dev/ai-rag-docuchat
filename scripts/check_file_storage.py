
import asyncio
from pathlib import Path

from fastapi import UploadFile

from app.services.file_storage import save_uploaded_file



async def main() -> None:
    test_content = b"Hello from DocuChat!"
    test_file = UploadFile(
        filename="test.txt",
        file=__import__("io").BytesIO(test_content),
    )

    saved_path = await save_uploaded_file(test_file)

    print(f"Saved path: {saved_path}")
    print(f"File exists: {saved_path.is_file()}")
    print(f"Content matches: {saved_path.read_bytes() == test_content}")

    saved_path.unlink()


if __name__ == "__main__":
    asyncio.run(main())
