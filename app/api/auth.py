from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import AuthResponse, FirebaseAuthRequest, UserProfile
from app.services.auth_service import get_or_create_user, verify_firebase_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse)
async def login_with_firebase(
    request: FirebaseAuthRequest,
    db: Session = Depends(get_db),
):
    firebase_user = await verify_firebase_token(request.id_token)
    if not firebase_user:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

    user = await get_or_create_user(firebase_user)

    return AuthResponse(
        access_token=request.id_token,
        uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: dict = Depends(get_current_user),
):
    return UserProfile(
        uid=current_user["uid"],
        email=current_user["email"],
        display_name=current_user.get("display_name"),
        photo_url=current_user.get("photo_url"),
    )


@router.post("/verify")
async def verify_token(
    request: FirebaseAuthRequest,
):
    firebase_user = await verify_firebase_token(request.id_token)
    if not firebase_user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"valid": True, "uid": firebase_user["uid"]}
