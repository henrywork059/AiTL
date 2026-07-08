from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.mock import router as mock_router
from app.routes.traffic import router as traffic_router

app = FastAPI(title="AI Traffic Light PC Studio Backend", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_router, prefix="/api/mock", tags=["mock"])
app.include_router(traffic_router, prefix="/api/traffic", tags=["traffic"])


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": "pc-studio-backend",
        "version": "0.0.1",
        "mode": "mock",
    }
