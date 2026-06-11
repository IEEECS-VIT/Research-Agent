import os
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "gemini_key_set": bool(settings.gemini_api_key),
        "firebase_configured": bool(settings.firebase_credentials_path),
    }
