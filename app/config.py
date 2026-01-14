import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    FIREBASE_CONFIG = {
        "apiKey": os.environ.get("FB_API_KEY", ""),
        "authDomain": os.environ.get("FB_AUTH_DOMAIN", ""),
        "databaseURL": os.environ.get("FB_DB_URL", ""),
        "projectId": os.environ.get("FB_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FB_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FB_MSG_SENDER_ID", ""),
        "appId": os.environ.get("FB_APP_ID", ""),
    }




