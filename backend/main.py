"""
main.py
-------
FastAPI application.  Run with:

    uvicorn main:app --reload --port 8000

Current routes
--------------
  POST /feedback   – save a helpfulness rating (+ optional comment)
  POST /subscribe  – save an email address for the weekly digest
"""

import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from database import get_connection, init_db


# ---------------------------------------------------------------------------
# Lifespan: runs init_db() once when the server starts
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [SQLite] Create tables on startup if they don't already exist
    init_db()
    yield


app = FastAPI(title="CS394 Backend", lifespan=lifespan)


# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any future production origin
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:5174",   # Vite dev (fallback port)
        "http://localhost:4173",   # Vite preview
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FeedbackPayload(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Helpfulness score 1–5")
    comment: Optional[str] = Field(None, max_length=2000)


class SubscribePayload(BaseModel):
    email: EmailStr


class OKResponse(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post(
    "/feedback",
    response_model=OKResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a helpfulness rating",
)
def submit_feedback(payload: FeedbackPayload):
    """
    Accepts a rating (1–5) and an optional comment.
    Persisted to the [SQLite] `feedback` table.
    Ratings of 3 or below should include a comment from the frontend
    (enforced in the UI; the backend accepts any payload gracefully).
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO feedback (rating, comment) VALUES (?, ?)",
                (payload.rating, payload.comment or None),
            )
    finally:
        conn.close()

    return OKResponse()


@app.post(
    "/subscribe",
    response_model=OKResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to the weekly email digest",
)
def subscribe(payload: SubscribePayload):
    """
    Stores an email address in the [SQLite] `email_subscriptions` table.
    Duplicate addresses are silently accepted (UNIQUE constraint on the
    DB side means the row just isn't re-inserted).
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO email_subscriptions (email) VALUES (?)",
                (str(payload.email),),
            )
    except sqlite3.IntegrityError:
        # [SQLite] UNIQUE constraint — address already subscribed, not an error
        pass
    finally:
        conn.close()

    return OKResponse()
