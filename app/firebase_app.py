"""Firebase initialization for StudyBuddy.

We keep Pyrebase for Authentication (email/password sign-in),
but we use Firebase Admin SDK for Realtime Database access.

Reason: Admin SDK avoids RTDB REST token issues (401 / Permission denied)
when the backend needs to write data for different users.

The `db` object exposed by this module mimics the small subset of the
Pyrebase DB API used in routes: `.child(...).get/set/update/remove(...)`.
Token arguments are accepted but ignored (Admin SDK does not need them).
"""

from __future__ import annotations

import os
from typing import Any, Optional

import pyrebase

import firebase_admin
from firebase_admin import credentials as admin_credentials
from firebase_admin import db as admin_db


firebase = None
auth = None

db = None  # will be set to a Pyrebase-like wrapper over Admin SDK
DATABASE_URL = None


# Default location of the service account key in this repo
DEFAULT_SERVICE_ACCOUNT_PATH = "app/studybuddyismai-firebase-adminsdk-fbsvc-73c23ec017.json"


class _GetResult:
    """Mimics Pyrebase get() return object (supports .val())."""

    def __init__(self, data: Any):
        self._data = data

    def val(self) -> Any:
        return self._data


class _AdminRTDB:
    """Tiny wrapper that looks like Pyrebase's db API for our app usage."""

    def __init__(self, ref: admin_db.Reference):
        self._ref = ref

    def child(self, path: str) -> "_AdminRTDB":
        clean = (path or "").strip("/")
        return _AdminRTDB(self._ref.child(clean))

    # Pyrebase supports token=...; we accept it to keep routes unchanged
    def get(self, token: Optional[str] = None) -> _GetResult:  # noqa: ARG002
        return _GetResult(self._ref.get())

    def set(self, data: Any, token: Optional[str] = None) -> None:  # noqa: ARG002
        self._ref.set(data)

    def update(self, data: dict, token: Optional[str] = None) -> None:  # noqa: ARG002
        self._ref.update(data)

    def remove(self, token: Optional[str] = None) -> None:  # noqa: ARG002
        self._ref.delete()

    # Convenience: sometimes code uses `.push(...)`
    def push(self, data: Any, token: Optional[str] = None) -> dict:  # noqa: ARG002
        new_ref = self._ref.push(data)
        return {"name": new_ref.key}


def _init_admin_sdk(database_url: str, service_account_path: str) -> None:
    """Initialize Admin SDK once."""
    if firebase_admin._apps:
        return

    # Allow relative paths (from project root) or absolute paths
    sa_path = service_account_path
    if not os.path.isabs(sa_path):
        # Resolve relative to project root (one level above this file's directory)
        here = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(here, ".."))
        sa_path = os.path.normpath(os.path.join(project_root, sa_path))

    cred = admin_credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred, {"databaseURL": database_url})


def init_firebase(app) -> None:
    """Init Pyrebase auth + Admin SDK RTDB wrapper."""
    global firebase, auth, db, DATABASE_URL

    config = app.config.get("FIREBASE_CONFIG") or {}

    # Pyrebase for Authentication (login/register)
    firebase = pyrebase.initialize_app(config)
    auth = firebase.auth()

    # Admin SDK for Realtime Database
    DATABASE_URL = (config.get("databaseURL") or "").rstrip("/")
    if not DATABASE_URL:
        raise RuntimeError("FIREBASE_CONFIG.databaseURL is missing")

    # Service account path can be overridden via app config
    service_account_path = (
        app.config.get("FIREBASE_SERVICE_ACCOUNT")
        or os.getenv("FIREBASE_SERVICE_ACCOUNT")
        or DEFAULT_SERVICE_ACCOUNT_PATH
    )

    _init_admin_sdk(DATABASE_URL, service_account_path)

    # Expose db wrapper with Pyrebase-like API
    db = _AdminRTDB(admin_db.reference("/"))


# Backwards-compat helper kept (some code imports this)

def rtdb_patch(path: str, data: dict, id_token: str | None = None):
    """PATCH-like update (kept for compatibility).

    With Admin SDK we can just do an update(). `id_token` is accepted but ignored.
    """
    if db is None:
        raise RuntimeError("db is not configured. Did you call init_firebase(app)?")

    clean = (path or "").lstrip("/")
    node = db
    for part in clean.split("/"):
        if part:
            node = node.child(part)
    node.update(data)
    return True
