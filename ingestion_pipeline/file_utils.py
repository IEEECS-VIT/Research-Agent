import shutil
from pathlib import Path
import traceback

UPLOAD_DIR = Path("uploads")

def validate_extension(filename: str) -> bool:
    try:
        return filename.lower().endswith((".pdf", ".docx", ".html"))
    except Exception as e:
        print(f"[FILE_UTILS] Error validating extension: {e}")
        return False

async def save_upload(file) -> Path:
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        path = UPLOAD_DIR / file.filename
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return path
    except Exception as e:
        print(f"[FILE_UTILS] Error saving upload: {e}")
        traceback.print_exc()
        raise

def cleanup(path: Path | str):
    try:
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
            print(f"[FILE_UTILS] Cleaned up temporary file: {path}")
    except Exception as e:
        print(f"[FILE_UTILS] Failed to clean up {path}: {e}")