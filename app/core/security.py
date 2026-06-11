from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import verify_firebase_token, get_or_create_user

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = None

    if credentials:
        token = credentials.credentials

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_data = await verify_firebase_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    await get_or_create_user(user_data)

    return user_data


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict | None:
    token = None

    if credentials:
        token = credentials.credentials

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    return await verify_firebase_token(token)
