import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # You can replace these with env vars if chceš, ale teraz dávam tvoje reálne hodnoty
    FIREBASE_CONFIG = {
        "apiKey": os.environ.get("FB_API_KEY", "AIzaSyBEixqtDWAQoxNoqi8tv0Lpfoc3t8Kud4w"),
        "authDomain": os.environ.get("FB_AUTH_DOMAIN", "studybuddy-61a4a.firebaseapp.com"),
        "databaseURL": os.environ.get("FB_DB_URL", "https://studybuddy-61a4a-default-rtdb.europe-west1.firebasedatabase.app"),
        "projectId": os.environ.get("FB_PROJECT_ID", "studybuddy-61a4a"),
        "storageBucket": os.environ.get("FB_STORAGE_BUCKET", "studybuddy-61a4a.firebasestorage.app"),
        "messagingSenderId": os.environ.get("FB_MSG_SENDER_ID", "576039481434"),
        "appId": os.environ.get("FB_APP_ID", "1:576039481434:web:19e7582bef488b573f6863")
    }
