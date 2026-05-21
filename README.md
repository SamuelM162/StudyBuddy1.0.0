# StudyPeer

StudyPeer is a Flask + Firebase student community app with profiles, study matching, tutoring, ride sharing, chat, friends, and institution-based discovery.

## Local run

The existing localhost workflow stays the same:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

Open `http://127.0.0.1:5001`.

Notes:
- `run.py` respects `PORT` and defaults to `5001` locally to avoid common macOS port 5000 conflicts.
- Debug stays off when `FLASK_ENV=production`.
- The app still loads `.env` from the project root.

## Required environment variables

Application:

```env
SECRET_KEY=
FLASK_ENV=development
FLASK_DEBUG=0
PORT=5001
WEB_CONCURRENCY=2
GROQ_API_KEY=
```

Firebase Web SDK:

```env
FB_API_KEY=
FB_AUTH_DOMAIN=
FB_DB_URL=
FB_PROJECT_ID=
FB_STORAGE_BUCKET=
FB_MSG_SENDER_ID=
FB_APP_ID=
```

Firebase Admin credentials:

Use one of these:

```env
FIREBASE_ADMIN_JSON=
FIREBASE_SERVICE_ACCOUNT=
```

Recommended for Render/Railway:
- Set `FIREBASE_ADMIN_JSON` to the full service-account JSON as a single line.
- Keep `private_key` newlines escaped as `\n`.

Optional local fallback:
- `FIREBASE_SERVICE_ACCOUNT` can point to a local JSON file path.
- Local admin JSON files should not be committed.

## Docker

Build and run locally:

```bash
docker build -t studypeer .
docker run --env-file .env -p 5001:5001 studypeer
```

Production container behavior:
- Starts with Gunicorn
- Binds to `0.0.0.0:${PORT}`
- Defaults to Dockerfile `PORT=8080` unless your environment sets `PORT`
- Forces `FLASK_ENV=production`
- Keeps Flask debug off

## Deploy on Google Cloud Run

The repo includes `cloudbuild.yaml` for Cloud Build + Cloud Run. It builds the Docker image, pushes it to Artifact Registry, and deploys the Cloud Run service.

Recommended one-time setup:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com

gcloud artifacts repositories create studypeer \
  --repository-format=docker \
  --location=europe-west1 \
  --description="StudyPeer containers"
```

Create required secrets:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY

printf 'PASTE_SECRET_KEY_HERE' | gcloud secrets create studypeer-secret-key --data-file=-
gcloud secrets create studypeer-firebase-admin-json --data-file=/path/to/firebase-service-account.json
```

Allow the Cloud Run runtime service account to read secrets. Replace `PROJECT_NUMBER` with the value from `gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'`.

```bash
gcloud secrets add-iam-policy-binding studypeer-secret-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding studypeer-firebase-admin-json \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Deploy:

```bash
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_REGION=europe-west1,_SERVICE=studypeer,_REPOSITORY=studypeer,_IMAGE=studypeer,_FB_API_KEY="...",_FB_AUTH_DOMAIN="...",_FB_DB_URL="...",_FB_PROJECT_ID="...",_FB_STORAGE_BUCKET="...",_FB_MSG_SENDER_ID="...",_FB_APP_ID="..."
```

Optional AI secret:

```bash
printf 'PASTE_GROQ_API_KEY_HERE' | gcloud secrets create studypeer-groq-api-key --data-file=-
gcloud secrets add-iam-policy-binding studypeer-groq-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud run services update studypeer \
  --region=europe-west1 \
  --set-secrets=GROQ_API_KEY=studypeer-groq-api-key:latest
```

Cloud Run notes:
- Cloud Run injects `PORT`; the Dockerfile listens on `0.0.0.0:${PORT}` with a fallback of `8080`.
- `SECRET_KEY` and `FIREBASE_ADMIN_JSON` are loaded from Secret Manager.
- `.gcloudignore` keeps local env files and Firebase JSON keys out of the uploaded build context.
- If deploy succeeds but the app does not start, check Cloud Run logs for missing `FB_DB_URL`, invalid Firebase admin JSON, or missing Secret Manager permissions.

## Deploy on Render

1. Create a new Web Service from this repo.
2. Choose `Docker` as the runtime.
3. Add the environment variables from `.env.example`.
4. Set `SECRET_KEY` to a strong random value.
5. Paste your Firebase service account into `FIREBASE_ADMIN_JSON`.
6. Deploy. Render will provide `PORT` automatically.

Recommended Render settings:
- Start command: leave empty when using the provided `Dockerfile`
- Health check path: `/`

## Deploy on Railway

1. Create a new project and connect this repo.
2. Deploy using the included `Dockerfile`.
3. Add the same environment variables as on Render.
4. Set `SECRET_KEY` and `FIREBASE_ADMIN_JSON`.
5. Redeploy after variables are saved.

Railway also injects `PORT` automatically, so no code change is needed.

## Security notes

- Do not hardcode secrets in code, templates, or Docker files.
- Do not commit `.env` or Firebase admin JSON credentials.
- Form submissions use CSRF protection.
- Friend actions and institution pages require login.

## Quick troubleshooting

- `RuntimeError: FIREBASE_CONFIG.databaseURL is missing`
  - Check `FB_DB_URL`.
- Firebase admin init fails
  - Re-check `FIREBASE_ADMIN_JSON` formatting or `FIREBASE_SERVICE_ACCOUNT`.
- Container starts but app is unreachable
  - Confirm the deploy platform is passing `PORT` and that the service is exposed publicly.
