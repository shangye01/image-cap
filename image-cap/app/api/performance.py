from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.auth import _require_current_user
from app.db.session import get_db
from app.services.user_performance import build_user_performance_summary

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/me/summary")
def get_my_performance_summary(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    return {
        "summary": build_user_performance_summary(db, user.id),
    }
