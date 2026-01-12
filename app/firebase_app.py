import pyrebase
import requests
import traceback

firebase = None
auth = None
db = None
DATABASE_URL = None

def init_firebase(app):
    global firebase, auth, db, DATABASE_URL
    config = app.config.get("FIREBASE_CONFIG")
    firebase = pyrebase.initialize_app(config)
    auth = firebase.auth()
    db = firebase.database()

    # Base URL for direct RTDB REST calls (used to bypass Pyrebase path issues)
    DATABASE_URL = (config.get("databaseURL") or "").rstrip("/")



def rtdb_patch(path: str, data: dict, id_token: str | None = None):
    """PATCH data to RTDB at the given path (e.g. 'users/<uid>'). Bypasses Pyrebase path issues."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured. Did you call init_firebase(app)?")

    clean = (path or "").lstrip("/")
    url = f"{DATABASE_URL}/{clean}.json"

    params = {}
    if id_token:
        params["auth"] = id_token

    resp = requests.patch(url, json=data, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
