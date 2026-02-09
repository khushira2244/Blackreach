Backend Setup & Running Instructions

This backend powers Blackreach’s journey reasoning, lookahead analysis, and Gemini-based decision engine.
It is built with FastAPI and integrates Firebase and Google Vertex AI (Gemini).

Prerequisites

Python 3.10+

Google Cloud project with:

Vertex AI enabled

Service Account JSON key

Firebase project with Realtime Database enabled

1) Clone & Enter Backend
git clone <your-repo-url>
cd backend

2) Create Python Virtual Environment
python -m venv .venv

Activate (Windows – PowerShell)
.\.venv\Scripts\Activate.ps1


If activation is blocked, run once:

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

Activate (macOS / Linux)
source .venv/bin/activate

3) Install Dependencies
python -m pip install --upgrade pip
pip install fastapi uvicorn httpx python-dotenv pydantic firebase-admin google-genai


These packages cover:

API server

Firebase access

Gemini / Vertex AI calls

Environment configuration

4) Environment Variables (.env)

Create a file named .env in the backend root.

Example .env file
# ─────────────────────────────
# Firebase
# ─────────────────────────────
FIREBASE_SERVICE_ACCOUNT_PATH=secrets/firebase-service-account.json
FIREBASE_DATABASE_URL=https://<your-project>.firebaseio.com

# ─────────────────────────────
# Google Cloud / Vertex AI
# ─────────────────────────────
GOOGLE_CLOUD_PROJECT=third-camera-483403-c0
GOOGLE_CLOUD_LOCATION=asia-south1

# Gemini model used for reasoning
GEMINI_MODEL=gemini-2.5-flash

# Path to Vertex AI service account
VERTEX_SA_PATH=secrets/vertex-service-account.json

# Required by Google SDK
GOOGLE_APPLICATION_CREDENTIALS=backend/secrets/vertex-service-account.json

5) Secrets Directory Structure

Place your service account files here:

backend/
 ├─ secrets/
 │   ├─ firebase-service-account.json
 │   └─ vertex-service-account.json


⚠️ Never commit these files to Git
Add this to .gitignore:

secrets/
.env

6) Run the Backend Server
uvicorn api.main:app --reload --port 8000


If successful, you’ll see:

Uvicorn running on http://127.0.0.1:8000

7) API Docs (Swagger)

Open in browser:

http://localhost:8000/docs


You can test:

/booking/confirm

/tracking/update

/lookahead/500m

/gemini/run/{bookingId}
