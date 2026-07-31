import json
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import get_settings

settings = get_settings()

_firebase_app = None


def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        if settings.firebase_credentials_path:
            cred_path = settings.firebase_credentials_path
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                try:
                    cred_dict = json.loads(cred_path)
                    cred = credentials.Certificate(cred_dict)
                except json.JSONDecodeError:
                    raise RuntimeError(
                        "FIREBASE_CREDENTIALS_PATH must be a valid file path or JSON string"
                    )
        else:
            raise RuntimeError("FIREBASE_CREDENTIALS_PATH not set")

        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


@lru_cache
def get_firebase_auth():
    get_firebase_app()
    return auth
