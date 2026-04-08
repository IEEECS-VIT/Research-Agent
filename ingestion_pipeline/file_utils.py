import shutil
from pathlib import Path


UPLOAD_DIR = Path("uploads")


def validate_extension(filename):
    return filename.endswith((".pdf", ".docx", ".html"))


async def save_upload(file):
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return path


def cleanup(path):
    try:
        Path(path).unlink()
    except:
        pass