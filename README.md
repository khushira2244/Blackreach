
## 🔐 Security & Credential Notice

For hackathon deployment purposes, this project originally used Google Cloud and Firebase service account credentials.

⚠️ All previously used service accounts and the associated Google Cloud project have been permanently deleted.

- No active cloud resources are running.
- Any previously committed credentials have been revoked.
- To run this project locally, you must create your own Firebase and Google Cloud project and provide your own service account credentials.

This ensures security best practices and prevents misuse of cloud resources.




📘 Blackreach
What is Blackreach?

Blackreach is a real-time contextual safety system designed for moments where GPS tracking alone is not enough.


<img width="1895" height="942" alt="image" src="https://github.com/user-attachments/assets/411b5d8b-44ca-451d-bd9c-e40aa2eb4b59" />

Traditional safety applications react after an emergency happens.
Blackreach works earlier — during uncertainty.

It continuously reasons about:

Where a user is going

What type of environment they are entering

Whether the journey is behaving as expected

How risk evolves minute by minute

Instead of panic buttons and reactive alerts, Blackreach provides calm, context-aware escalation.

It is built for:

Women and children commuting daily

Elderly individuals traveling independently

Travelers in unfamiliar areas

Security teams needing structured situational awareness

Blackreach bridges digital reasoning and physical response — without overwhelming the user.

🧠 Core Idea

Blackreach operates in three intelligent layers:

1️⃣ Context Sensing

Live GPS tracking

500m Lookahead environmental audit

Route intent & deviation awareness

2️⃣ Gemini-Based Reasoning

Risk classification (GREEN / ORANGE / RED)

Adaptive vigilance (dynamic FPS scaling)

Context-aware escalation logic

3️⃣ Human-in-the-Loop Response

Structured reasoning briefs

Subcenter / response activation

Manual or automatic emergency transition

Emergency is treated as a state, not just a button.


<img width="1884" height="883" alt="image" src="https://github.com/user-attachments/assets/fc984b1a-56f3-47d2-97fd-9ed50ff76e09" />

Key Capabilities

500m lookahead risk audit

Adaptive monitoring profiles

Gemini contextual reasoning engine

Live visual signal analysis (image-based emergency demo)

Human-backed escalation pipeline

Clean UI transitions without panic-driven interaction

🧠 System Architecture Overview
User Tracking
      ↓
Lookahead Engine
      ↓
Gemini Reasoning
      ↓
Risk Classification
      ↓
UI / Subcenter Action
Flow Explanation

Tracking captures movement signals.

Lookahead evaluates environmental context.

Gemini synthesizes journey intent + risk signals.

UI transitions based on risk state.

Subcenters activate only when thresholds are crossed.

<img width="1892" height="712" alt="image" src="https://github.com/user-attachments/assets/7b5c55bf-724b-4e4c-a317-515b94f53f17" />

🔧 Backend Setup & Running Instructions

This backend powers Blackreach’s journey reasoning, lookahead analysis, and Gemini-based decision engine.

Built with:

FastAPI

Firebase Realtime Database

Google Vertex AI (Gemini)

📦 Prerequisites

#  I have used the Gemini 3.0 , but it is not in the env file, it is hardcoded in routes files , but for
fast reasoning forlookahead , I used gemini 2.5

Python 3.10+

Google Cloud project with Vertex AI enabled

Firebase project with Realtime Database enabled

Service Account JSON keys for both

1️⃣ Clone & Enter Backend
git clone <your-repo-url>
cd backend
2️⃣ Create Python Virtual Environment
python -m venv .venv
Activate (Windows – PowerShell)
.\.venv\Scripts\Activate.ps1

If blocked:

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
Activate (macOS / Linux)
source .venv/bin/activate
3️⃣ Install Dependencies
python -m pip install --upgrade pip
pip install fastapi uvicorn httpx python-dotenv pydantic firebase-admin google-genai
4️⃣ Environment Variables (.env)

Create .env in backend root.

# Firebase
FIREBASE_SERVICE_ACCOUNT_PATH=secrets/firebase-service-account.json
FIREBASE_DATABASE_URL=https://<your-project>.firebaseio.com

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=asia-south1

# Gemini Model
GEMINI_MODEL=gemini-2.5-flash

# Vertex AI Service Account
VERTEX_SA_PATH=secrets/vertex-service-account.json
GOOGLE_APPLICATION_CREDENTIALS=backend/secrets/vertex-service-account.json
5️⃣ Secrets Directory Structure
backend/
 ├─ secrets/
 │   ├─ firebase-service-account.json
 │   └─ vertex-service-account.json

Add to .gitignore:

secrets/
.env
6️⃣ Run Backend Server
uvicorn api.main:app --reload --port 8000

Access API docs at:

http://localhost:8000/docs
Available Endpoints

/booking/confirm

/tracking/update

/lookahead/500m

/gemini/run/{bookingId}

/video/emergency-demo

💻 Frontend Setup (Vite + React)

The frontend is built using Vite + React.

No environment variables are required for demo reliability.



1️⃣ Enter Frontend Directory
cd frontend
2️⃣ Install Dependencies
npm install
3️⃣ Run Development Server
npm run dev

Runs at:

http://localhost:5173

Backend assumed at:

http://localhost:8000
🎯 Demo Flow Summary

Confirm journey

Start tracking

Enter security zone

Gemini reasoning triggers

Risk classification updates UI

LiveEye simulates emergency image

System transitions to Emergency state

🧩 Philosophy

Blackreach is not a panic system.
It is a reasoning system.

It does not wait for danger.
It watches for deviation.

It does not escalate noise.
It escalates context.

