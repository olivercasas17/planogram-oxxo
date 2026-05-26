import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import optimize, upload

load_dotenv()

app = FastAPI(title="Planogram OXXO API")

_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in _origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(optimize.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
