# StudyBuddy – Flask + Firebase + Social App

StudyBuddy is a Flask web application using Firebase (Auth + Realtime Database) for a social student platform.

## Features
- Firebase Auth (email/password)
- Student profiles (faculty, interests/subjects, tutor flag)
- Study matching (suggested connections by common subjects)
- Friend requests + friends list + messaging
- Tutoring offers + tutoring requests
- Ride sharing (create/join rides)
- AI chatbot widget (Groq / LLaMA)
- Dark/Light theme toggle (Bootstrap 5)
- Responsive layout usable on phone

## Setup (Local)

### 1) Create virtual environment and install dependencies

~~~bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
~~~

### 2) Create a .env file

This project loads configuration and secrets from environment variables.

Create a `.env` file in the project root:

~~~env
SECRET_KEY=dev-secret-key-change-me

GROQ_API_KEY=YOUR_GROQ_API_KEY

FB_API_KEY=
FB_AUTH_DOMAIN=
FB_DB_URL=
FB_PROJECT_ID=
FB_STORAGE_BUCKET=
FB_MSG_SENDER_ID=
FB_APP_ID=

FIREBASE_ADMIN_JSON=
~~~

Notes:
- `FIREBASE_ADMIN_JSON` must contain the full Firebase service account JSON in one line.
- In the JSON, `private_key` must use escaped newlines (`\n`), not real line breaks.
- You can convert your service account json to a single-line string using:

~~~bash
python -c 'import json; print(json.dumps(json.load(open("firebase-admin.json"))))'
~~~

Then paste that output into `.env` after `FIREBASE_ADMIN_JSON=`.

### 3) Run the app

~~~bash
python run.py
~~~

Open:
http://127.0.0.1:5000

## Security

Do not commit secrets. Add to `.gitignore`:

~~~gitignore
.env
*.json
~~~

## Troubleshooting

- If you see `RuntimeError: FIREBASE_CONFIG.databaseURL is missing`, check that `FB_DB_URL` exists in `.env` and that `.env` is loaded.
- If you see `groq.AuthenticationError: Invalid API Key`, check that `GROQ_API_KEY` exists in `.env` and is valid.