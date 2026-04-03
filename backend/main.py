"""
main.py
-------
FastAPI application entry point.  Run with:

    uvicorn main:app --reload --port 8000

Mounts two fully isolated routers:
  /feedback-system — POST /feedback, POST /subscribe
  /query-system    — POST /query, GET /list, GET /document/{path}  (coming soon)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.feedback_router import router as feedback_router
from routers.query_router import router as query_router
from feedback_system.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SH-BAM Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback_router, prefix="/feedback-system")
app.include_router(query_router, prefix="/query-system")
