import os
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Directory where uploads are stored (relative to project root)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file extensions for document ingestion
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".pptx", ".xlsx"}

def validate_extension(filename: str) -> bool:
    """Return True if the file has an allowed extension, False otherwise."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

async def save_upload(file: UploadFile) -> Path:
    """Save an uploaded file to the temporary uploads directory and return the path.

    The function writes the file in chunks to avoid loading the whole file into memory.
    """
    # Ensure the upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = UPLOAD_DIR / file.filename
    try:
        with open(tmp_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # read in 1MB chunks
                buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
    finally:
        await file.close()
    return tmp_path

def cleanup(path: Path) -> None:
    """Delete a temporary file or directory if it exists."""
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
    except Exception as e:
        # Log but do not raise; cleanup should be best‑effort
        print(f"[FILE_UTILS] Cleanup warning: {e}")
