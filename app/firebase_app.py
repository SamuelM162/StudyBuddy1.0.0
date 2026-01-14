"""
Firebase initialization for StudyBuddy.

We use Firebase Admin SDK for Realtime Database access.

Pyrebase (legacy) is OPTIONAL for email/password auth, but it is not imported
at module import-time (to avoid gcloud/pkg_resources deprecation warnings).
If you still need Pyrebase auth, enable it explicitly via:
    app.config["USE_PYREBASE_AUTH"] = True

The `db` object exposed by this module mimics the small subset of the
Pyrebase DB API used in routes: `.child(...).get/set/update/remove(...)`.
Token arguments are accepted but ignored (Admin SDK does not need them).
"""

from __future__ import annotations

import os
import json
from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials as admin_credentials
from firebase_admin import db as admin_db
from firebase_admin import auth as admin_auth


firebase = None
auth = None

db = None  # will be set to a Pyrebase-like wrapper over Admin SDK
DATABASE_URL = None


# Default location of the service account key in this repo (fallback only)
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


def _init_admin_sdk(database_url: str, cred_source: Any) -> None:
    """Initialize Admin SDK once.

    cred_source can be:
      - dict: parsed service account JSON (from env)
      - str: path to service account JSON file (fallback)
    """
    if firebase_admin._apps:
        return

    # If env JSON dict was provided
    if isinstance(cred_source, dict):
        cred = admin_credentials.Certificate(cred_source)
        firebase_admin.initialize_app(cred, {"databaseURL": database_url})
        return

    # Otherwise treat as a path string
    service_account_path = str(cred_source)
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

    # Optional Pyrebase auth (legacy) — only if explicitly enabled.
    # Default: do NOT import Pyrebase to avoid legacy gcloud/pkg_resources warnings.
    if app.config.get("USE_PYREBASE_AUTH", False):
        from pyrebase import initialize_app  # local import on purpose

        firebase = initialize_app(config)
        auth = firebase.auth()
    else:
        firebase = None
        auth = admin_auth  # expose Admin auth for token verification helpers if needed

    # Admin SDK for Realtime Database
    DATABASE_URL = (config.get("databaseURL") or "").rstrip("/")
    if not DATABASE_URL:
        raise RuntimeError("FIREBASE_CONFIG.databaseURL is missing")

    # Prefer env JSON first (env-only secret)
    raw_json = os.getenv("FIREBASE_ADMIN_JSON")
    if raw_json:
        data = json.loads(raw_json)
        # dotenv often keeps newlines escaped as \\n
        if "private_key" in data and isinstance(data["private_key"], str):
            data["private_key"] = data["private_key"].replace("\\n", "\n")
        cred_source = data
    else:
        # Fallback to path (optional)
        cred_source = (
            app.config.get("FIREBASE_SERVICE_ACCOUNT")
            or os.getenv("FIREBASE_SERVICE_ACCOUNT")
            or DEFAULT_SERVICE_ACCOUNT_PATH
        )

    _init_admin_sdk(DATABASE_URL, cred_source)

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