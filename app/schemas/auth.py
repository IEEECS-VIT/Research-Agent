from pydantic import BaseModel


class FirebaseAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    uid: str
    email: str
    display_name: str | None = None
    photo_url: str | None = None


class UserProfile(BaseModel):
    uid: str
    email: str
    display_name: str | None = None
    photo_url: str | None = None
    is_active: bool = True


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    expires_in: int = 3600
