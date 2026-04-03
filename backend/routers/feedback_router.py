import sqlite3
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from feedback_system.database import get_connection

router = APIRouter()


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

@router.post("/feedback", response_model=OKResponse, status_code=201)
def submit_feedback(payload: FeedbackPayload):
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


@router.post("/subscribe", response_model=OKResponse, status_code=201)
def subscribe(payload: SubscribePayload):
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO email_subscriptions (email) VALUES (?)",
                (str(payload.email),),
            )
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
    return OKResponse()
