import os
import json
from functools import lru_cache

import aiohttp
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.config import get_settings
from app.utils.firebase import get_firebase_auth
from app.core.database import SessionLocal
from app.models.user import User

settings = get_settings()


async def verify_firebase_token(token: str) -> dict | None:
    try:
        firebase_auth = get_firebase_auth()
        decoded = firebase_auth.verify_id_token(token)
        return {
            "uid": decoded.get("uid", ""),
            "email": decoded.get("email", ""),
            "display_name": decoded.get("name", ""),
            "photo_url": decoded.get("picture", ""),
        }
    except Exception as e:
        pass

    try:
        decoded = id_token.verify_firebase_token(
            token,
            requests.Request(),
            audience=settings.firebase_project_id,
        )
        return {
            "uid": decoded.get("uid", ""),
            "email": decoded.get("email", ""),
            "display_name": decoded.get("name", ""),
            "photo_url": decoded.get("picture", ""),
        }
    except Exception as e:
        pass

    try:
        api_key = settings.firebase_api_key
        if not api_key:
            return None
        async with aiohttp.ClientSession() as session:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
            async with session.post(url, json={"idToken": token}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users = data.get("users", [])
                    if users:
                        u = users[0]
                        return {
                            "uid": u.get("localId", ""),
                            "email": u.get("email", ""),
                            "display_name": u.get("displayName", ""),
                            "photo_url": u.get("photoUrl", ""),
                        }
    except Exception:
        pass

    return None


async def get_or_create_user(firebase_user: dict) -> User:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            User.firebase_uid == firebase_user["uid"]
        ).first()

        if existing:
            existing.email = firebase_user.get("email", existing.email)
            if firebase_user.get("display_name"):
                existing.display_name = firebase_user["display_name"]
            if firebase_user.get("photo_url"):
                existing.photo_url = firebase_user["photo_url"]
            db.commit()
            db.refresh(existing)
            return existing

        user = User(
            firebase_uid=firebase_user["uid"],
            email=firebase_user.get("email", ""),
            display_name=firebase_user.get("display_name"),
            photo_url=firebase_user.get("photo_url"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()
