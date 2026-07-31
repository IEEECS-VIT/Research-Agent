import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")


def validate_extension(filename: str) -> bool:
    try:
        return filename.lower().endswith((".pdf", ".docx", ".html"))
    except Exception as e:
        logger.error("Error validating extension: %s", e)
        return False


import boto3
from botocore.exceptions import NoCredentialsError
from app.core.config import get_settings

async def save_upload(file) -> Path:
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        path = UPLOAD_DIR / file.filename
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Also upload to AWS S3
        settings = get_settings()
        if settings.aws_access_key_id and settings.aws_bucket_name:
            try:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region_name
                )
                s3.upload_file(str(path), settings.aws_bucket_name, file.filename)
                logger.info("Successfully uploaded %s to S3 bucket %s", file.filename, settings.aws_bucket_name)
            except NoCredentialsError:
                logger.error("AWS credentials not found. File saved locally only.")
            except Exception as e:
                logger.error("Failed to upload to S3: %s", e)
                
        return path
    except Exception as e:
        logger.error("Error saving upload: %s", e, exc_info=True)
        raise


def cleanup(path: Path | str):
    try:
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
            logger.info("Cleaned up temporary file: %s", path)
    except Exception as e:
        logger.warning("Failed to clean up %s: %s", path, e)
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def extract_doi(text: str) -> str | None:
    if not text:
        return None
    match = DOI_PATTERN.search(text)
    if match:
        # Clean any trailing punctuation that might be caught in the regex boundary
        return match.group(0).rstrip(".,;:")
    return None
