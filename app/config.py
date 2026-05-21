import os

class Config:
    ENV = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "development")).lower()
    IS_PRODUCTION = ENV == "production"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1" and not IS_PRODUCTION
    PORT = int(os.environ.get("PORT", "5001"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    PREFERRED_URL_SCHEME = "https" if IS_PRODUCTION else "http"
    FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")

    FIREBASE_CONFIG = {
        "apiKey": os.environ.get("FB_API_KEY", ""),
        "authDomain": os.environ.get("FB_AUTH_DOMAIN", ""),
        "databaseURL": os.environ.get("FB_DB_URL", ""),
        "projectId": os.environ.get("FB_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FB_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FB_MSG_SENDER_ID", ""),
        "appId": os.environ.get("FB_APP_ID", ""),
    }
