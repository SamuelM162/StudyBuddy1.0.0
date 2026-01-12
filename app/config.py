import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # You can replace these with env vars if chceš, ale teraz dávam tvoje reálne hodnoty
    FIREBASE_CONFIG = {
        "apiKey": os.environ.get("FB_API_KEY", "AIzaSyDWNLXPa76zEERPMuyrw25PHR6s4ZX73rc"),
        "authDomain": os.environ.get("FB_AUTH_DOMAIN", "studybuddyismai.firebaseapp.com"),
        "databaseURL": os.environ.get("FB_DB_URL", "https://studybuddyismai-default-rtdb.europe-west1.firebasedatabase.app"),
        "projectId": os.environ.get("FB_PROJECT_ID", "studybuddyismai"),
        "storageBucket": os.environ.get("FB_STORAGE_BUCKET", "studybuddyismai.firebasestorage.app"),
        "messagingSenderId": os.environ.get("FB_MSG_SENDER_ID", "1073210486444"),
        "appId": os.environ.get("FB_APP_ID", "1:1073210486444:web:9ea1ecbda292a81c8d3909"),
    }

    # Groq AI
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
