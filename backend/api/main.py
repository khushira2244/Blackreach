from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.journey import router as journey_router
from api.routers.booking import router as booking_router
from api.routers.tracking import router as tracking_router
from api.routers.case import router as case_router
from api.routers.center import router as center_router
from api.routers.chat import router as chat_router
from api.routers.gemini import router as gemini_router
from api.routers.lookahead import router as lookahead_router   # ✅ ADD THIS
from api.routers.video_emergency import router as video_emergency_router

app = FastAPI(title="Blackreach Backend", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(journey_router)
app.include_router(booking_router)
app.include_router(tracking_router)
app.include_router(case_router)
app.include_router(center_router)
app.include_router(chat_router)

app.include_router(lookahead_router)         # ✅ ADD THIS LINE
app.include_router(gemini_router)
app.include_router(video_emergency_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "blackreach-backend"}
