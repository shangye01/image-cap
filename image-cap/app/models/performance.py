from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnnotationTaskActivity(Base):
    __tablename__ = "annotation_task_activities"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_annotation_task_activity_task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    image_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)

    annotator_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    annotator_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    reviewer_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    task_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_saved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    save_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    work_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    submitted_annotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reviewed_annotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_annotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_changed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completion_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    efficiency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precision_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mean_iou: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    collaboration_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    collaboration_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    collaboration_review_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    collaboration_consistency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    last_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
