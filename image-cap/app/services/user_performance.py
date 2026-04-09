from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import AnnotationTaskActivity, User


def _utc_now() -> datetime:
    return datetime.utcnow()


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _round_score(value: float) -> float:
    return round(float(value or 0.0), 2)


def _serialize_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return None


def _ensure_task_activity(
    db: Session,
    task_id: str,
    task_row: dict[str, Any] | None = None,
) -> AnnotationTaskActivity:
    activity = (
        db.query(AnnotationTaskActivity)
        .filter(AnnotationTaskActivity.task_id == task_id)
        .first()
    )
    if activity:
        if task_row:
            activity.project_id = task_row.get("project_id") or activity.project_id
            activity.file_id = task_row.get("file_id") or activity.file_id
            activity.image_storage_path = (
                task_row.get("image_storage_path") or activity.image_storage_path
            )
        return activity

    activity = AnnotationTaskActivity(
        task_id=task_id,
        project_id=(task_row or {}).get("project_id"),
        file_id=(task_row or {}).get("file_id"),
        image_storage_path=(task_row or {}).get("image_storage_path"),
    )
    db.add(activity)
    db.flush()
    return activity


def _apply_user_binding(
    activity: AnnotationTaskActivity,
    user: User | None,
) -> None:
    if not user:
        return
    activity.annotator_user_id = user.id
    activity.annotator_username = user.username


def _compute_efficiency_score(work_seconds: float, annotation_count: int) -> float:
    if work_seconds <= 0:
        return 0.0
    speed_component = _clamp((600.0 / max(work_seconds, 60.0)) * 100.0)
    density_component = _clamp((annotation_count / max(work_seconds / 60.0, 1.0)) * 18.0)
    return _round_score(0.65 * speed_component + 0.35 * density_component)


def _box_iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    x1 = max(float(left.get("x", 0)), float(right.get("x", 0)))
    y1 = max(float(left.get("y", 0)), float(right.get("y", 0)))
    x2 = min(
        float(left.get("x", 0)) + float(left.get("width", 0)),
        float(right.get("x", 0)) + float(right.get("width", 0)),
    )
    y2 = min(
        float(left.get("y", 0)) + float(left.get("height", 0)),
        float(right.get("y", 0)) + float(right.get("height", 0)),
    )
    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter = inter_w * inter_h
    union = (
        float(left.get("width", 0)) * float(left.get("height", 0))
        + float(right.get("width", 0)) * float(right.get("height", 0))
        - inter
    )
    return inter / union if union > 0 else 0.0


def _match_annotations(
    submitted_annotations: list[dict[str, Any]],
    reviewed_annotations: list[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> dict[str, float]:
    if not submitted_annotations and not reviewed_annotations:
        return {
            "matched_count": 0,
            "precision": 100.0,
            "recall": 100.0,
            "mean_iou": 100.0,
            "accuracy": 100.0,
            "review_changed_count": 0,
        }

    used_review_indexes: set[int] = set()
    matched_count = 0
    iou_scores: list[float] = []

    for submitted in submitted_annotations:
        best_index = None
        best_iou = 0.0
        submitted_label = str(submitted.get("label", "")).strip().lower()
        for review_index, reviewed in enumerate(reviewed_annotations):
            if review_index in used_review_indexes:
                continue
            reviewed_label = str(reviewed.get("label", "")).strip().lower()
            if submitted_label != reviewed_label:
                continue
            current_iou = _box_iou(submitted, reviewed)
            if current_iou >= iou_threshold and current_iou > best_iou:
                best_iou = current_iou
                best_index = review_index

        if best_index is None:
            continue

        used_review_indexes.add(best_index)
        matched_count += 1
        iou_scores.append(best_iou)

    submitted_count = len(submitted_annotations)
    reviewed_count = len(reviewed_annotations)
    precision = (matched_count / submitted_count * 100.0) if submitted_count else 0.0
    recall = (matched_count / reviewed_count * 100.0) if reviewed_count else 0.0
    mean_iou = (sum(iou_scores) / len(iou_scores) * 100.0) if iou_scores else 0.0
    accuracy = 0.45 * precision + 0.35 * recall + 0.20 * mean_iou
    changed_count = max(submitted_count - matched_count, 0) + max(reviewed_count - matched_count, 0)
    return {
        "matched_count": matched_count,
        "precision": _round_score(precision),
        "recall": _round_score(recall),
        "mean_iou": _round_score(mean_iou),
        "accuracy": _round_score(accuracy),
        "review_changed_count": changed_count,
    }


def _derive_activity_score(submitted_count: int, recent_started_count: int) -> float:
    base = min(100.0, submitted_count * 8.0)
    recent_bonus = min(20.0, recent_started_count * 2.0)
    return _round_score(min(100.0, base + recent_bonus))


def _derive_stability_score(accuracies: list[float]) -> float:
    if len(accuracies) <= 1:
        return 100.0 if accuracies else 0.0
    avg = sum(accuracies) / len(accuracies)
    variance = sum((value - avg) ** 2 for value in accuracies) / len(accuracies)
    deviation = variance ** 0.5
    return _round_score(_clamp(100.0 - deviation * 1.5))


def _level_from_score(total_score: float) -> str:
    if total_score >= 90:
        return "A"
    if total_score >= 80:
        return "B"
    if total_score >= 70:
        return "C"
    if total_score >= 60:
        return "D"
    return "E"


def record_task_started(
    db: Session,
    task_id: str,
    user: User | None,
    task_row: dict[str, Any] | None = None,
    started_at: datetime | None = None,
) -> AnnotationTaskActivity:
    activity = _ensure_task_activity(db, task_id=task_id, task_row=task_row)
    _apply_user_binding(activity, user)
    if not activity.task_started_at:
        activity.task_started_at = started_at or _utc_now()
    db.commit()
    db.refresh(activity)
    return activity


def record_task_progress(
    db: Session,
    task_id: str,
    user: User | None,
    task_row: dict[str, Any] | None = None,
    *,
    started_at: datetime | None = None,
    last_saved_at: datetime | None = None,
    work_seconds: float | None = None,
    save_count_increment: int = 0,
    save_count_total: int | None = None,
    payload_snapshot: dict[str, Any] | None = None,
) -> AnnotationTaskActivity:
    activity = _ensure_task_activity(db, task_id=task_id, task_row=task_row)
    _apply_user_binding(activity, user)
    if not activity.task_started_at:
        activity.task_started_at = started_at or _utc_now()
    if not activity.first_saved_at:
        activity.first_saved_at = last_saved_at or _utc_now()
    activity.last_saved_at = last_saved_at or _utc_now()
    if work_seconds is not None:
        activity.work_seconds = max(activity.work_seconds, float(work_seconds or 0.0))
    if save_count_total is not None:
        activity.save_count = max(activity.save_count, int(save_count_total))
    if save_count_increment > 0:
        activity.save_count += int(save_count_increment)
    if payload_snapshot:
        activity.last_payload_json = _serialize_payload(payload_snapshot)
    db.commit()
    db.refresh(activity)
    return activity


def record_task_submission(
    db: Session,
    task_id: str,
    user: User | None,
    task_row: dict[str, Any] | None,
    submitted_annotations: list[dict[str, Any]],
    *,
    started_at: datetime | None = None,
    submitted_at: datetime | None = None,
    work_seconds: float | None = None,
    save_count: int | None = None,
    integration_result: dict[str, Any] | None = None,
    payload_snapshot: dict[str, Any] | None = None,
) -> AnnotationTaskActivity:
    activity = _ensure_task_activity(db, task_id=task_id, task_row=task_row)
    _apply_user_binding(activity, user)
    actual_started_at = started_at or activity.task_started_at or _utc_now()
    actual_submitted_at = submitted_at or _utc_now()
    activity.task_started_at = actual_started_at
    activity.submitted_at = actual_submitted_at
    if save_count is not None:
        activity.save_count = max(activity.save_count, int(save_count))
    if work_seconds is None:
        elapsed = max((actual_submitted_at - actual_started_at).total_seconds(), 0.0)
        work_seconds = elapsed
    activity.work_seconds = max(float(work_seconds or 0.0), activity.work_seconds)
    activity.submitted_annotation_count = len(submitted_annotations or [])
    activity.completion_score = 100.0
    activity.efficiency_score = _compute_efficiency_score(
        activity.work_seconds,
        activity.submitted_annotation_count,
    )
    if integration_result:
        activity.collaboration_ready = bool(integration_result.get("ready"))
        activity.collaboration_review_triggered = bool(
            integration_result.get("review_triggered")
        )
        consistency_scores = [
            float(item.get("consistency_score") or 0.0)
            for item in (integration_result.get("diff_highlights") or [])
            if item.get("consistency_score") is not None
        ]
        if consistency_scores:
            activity.collaboration_consistency_score = _round_score(
                sum(consistency_scores) / len(consistency_scores) * 100.0
            )
        elif integration_result.get("ready"):
            activity.collaboration_consistency_score = 100.0
        activity.collaboration_score = activity.collaboration_consistency_score
    if payload_snapshot:
        activity.last_payload_json = _serialize_payload(payload_snapshot)
    db.commit()
    db.refresh(activity)
    return activity


def record_review_result(
    db: Session,
    task_id: str,
    reviewer: User,
    reviewed_annotations: list[dict[str, Any]],
    submitted_annotations: list[dict[str, Any]] | None,
    *,
    reviewed_at: datetime | None = None,
    integration_result: dict[str, Any] | None = None,
) -> AnnotationTaskActivity:
    activity = _ensure_task_activity(db, task_id=task_id)
    activity.reviewer_user_id = reviewer.id
    activity.reviewer_username = reviewer.username
    activity.reviewed_at = reviewed_at or _utc_now()
    activity.reviewed_annotation_count = len(reviewed_annotations or [])

    match_result = _match_annotations(
        submitted_annotations or [],
        reviewed_annotations or [],
    )
    activity.matched_annotation_count = int(match_result["matched_count"])
    activity.review_changed_count = int(match_result["review_changed_count"])
    activity.precision_score = float(match_result["precision"])
    activity.recall_score = float(match_result["recall"])
    activity.mean_iou = float(match_result["mean_iou"])
    activity.accuracy_score = float(match_result["accuracy"])

    if integration_result:
        activity.collaboration_ready = bool(integration_result.get("ready"))
        activity.collaboration_review_triggered = bool(
            integration_result.get("review_triggered")
        )
        consistency_scores = [
            float(item.get("consistency_score") or 0.0)
            for item in (integration_result.get("diff_highlights") or [])
            if item.get("consistency_score") is not None
        ]
        if consistency_scores:
            activity.collaboration_consistency_score = _round_score(
                sum(consistency_scores) / len(consistency_scores) * 100.0
            )
    if activity.collaboration_consistency_score > 0:
        activity.collaboration_score = activity.collaboration_consistency_score

    activity.quality_score = _round_score(
        0.7 * activity.accuracy_score + 0.3 * activity.collaboration_score
    )
    activity.total_score = _round_score(
        0.50 * activity.accuracy_score
        + 0.25 * activity.efficiency_score
        + 0.15 * activity.collaboration_score
        + 0.10 * activity.completion_score
    )
    db.commit()
    db.refresh(activity)
    return activity


def build_user_performance_summary(
    db: Session,
    user_id: str,
    *,
    days: int = 30,
) -> dict[str, Any]:
    now = _utc_now()
    start_at = now - timedelta(days=max(days, 1))
    rows = (
        db.query(AnnotationTaskActivity)
        .filter(AnnotationTaskActivity.annotator_user_id == user_id)
        .order_by(AnnotationTaskActivity.created_at.desc())
        .all()
    )
    recent_rows = [
        row
        for row in rows
        if (row.submitted_at or row.task_started_at or row.created_at) >= start_at
    ]

    submitted_rows = [row for row in rows if row.submitted_at]
    recent_submitted_rows = [row for row in recent_rows if row.submitted_at]
    reviewed_rows = [row for row in rows if row.reviewed_at]
    recent_reviewed_rows = [row for row in recent_rows if row.reviewed_at]

    avg_work_seconds = (
        sum(max(row.work_seconds, 0.0) for row in recent_submitted_rows) / len(recent_submitted_rows)
        if recent_submitted_rows
        else 0.0
    )
    avg_annotations = (
        sum(row.submitted_annotation_count for row in recent_submitted_rows) / len(recent_submitted_rows)
        if recent_submitted_rows
        else 0.0
    )
    avg_efficiency = (
        sum(row.efficiency_score for row in recent_submitted_rows) / len(recent_submitted_rows)
        if recent_submitted_rows
        else 0.0
    )
    avg_accuracy = (
        sum(row.accuracy_score for row in recent_reviewed_rows) / len(recent_reviewed_rows)
        if recent_reviewed_rows
        else 0.0
    )
    avg_collaboration = (
        sum(row.collaboration_score for row in recent_rows) / len(recent_rows)
        if recent_rows
        else 0.0
    )
    avg_quality = (
        sum(row.quality_score for row in recent_reviewed_rows) / len(recent_reviewed_rows)
        if recent_reviewed_rows
        else 0.0
    )
    activity_score = _derive_activity_score(
        submitted_count=len(recent_submitted_rows),
        recent_started_count=len(recent_rows),
    )
    stability_score = _derive_stability_score(
        [row.accuracy_score for row in recent_reviewed_rows if row.accuracy_score > 0]
    )
    completion_rate = (
        len(recent_submitted_rows) / len(recent_rows) * 100.0 if recent_rows else 0.0
    )
    reviewed_rate = (
        len(recent_reviewed_rows) / len(recent_submitted_rows) * 100.0
        if recent_submitted_rows
        else 0.0
    )
    total_score = _round_score(
        0.45 * avg_accuracy
        + 0.20 * avg_efficiency
        + 0.15 * avg_collaboration
        + 0.10 * activity_score
        + 0.10 * stability_score
    )

    previous_start = start_at - timedelta(days=max(days, 1))
    previous_rows = [
        row
        for row in rows
        if previous_start <= (row.submitted_at or row.task_started_at or row.created_at) < start_at
    ]
    previous_reviewed_rows = [row for row in previous_rows if row.reviewed_at]
    previous_submitted_rows = [row for row in previous_rows if row.submitted_at]
    previous_accuracy = (
        sum(row.accuracy_score for row in previous_reviewed_rows) / len(previous_reviewed_rows)
        if previous_reviewed_rows
        else 0.0
    )
    previous_efficiency = (
        sum(row.efficiency_score for row in previous_submitted_rows) / len(previous_submitted_rows)
        if previous_submitted_rows
        else 0.0
    )
    previous_total = _round_score(
        0.45 * previous_accuracy
        + 0.20 * previous_efficiency
        + 0.15 * (
            sum(row.collaboration_score for row in previous_rows) / len(previous_rows)
            if previous_rows
            else 0.0
        )
        + 0.10 * _derive_activity_score(len(previous_submitted_rows), len(previous_rows))
        + 0.10 * _derive_stability_score(
            [row.accuracy_score for row in previous_reviewed_rows if row.accuracy_score > 0]
        )
    )

    return {
        "user_id": user_id,
        "period_days": days,
        "has_data": bool(rows),
        "level": _level_from_score(total_score),
        "totals": {
            "all_started_tasks": len(rows),
            "all_submitted_tasks": len(submitted_rows),
            "all_reviewed_tasks": len(reviewed_rows),
            "recent_started_tasks": len(recent_rows),
            "recent_submitted_tasks": len(recent_submitted_rows),
            "recent_reviewed_tasks": len(recent_reviewed_rows),
        },
        "mvp": {
            "completion_rate": _round_score(completion_rate),
            "review_coverage": _round_score(reviewed_rate),
            "avg_task_minutes": _round_score(avg_work_seconds / 60.0),
            "avg_annotations_per_task": _round_score(avg_annotations),
        },
        "scores": {
            "speed": _round_score(avg_efficiency),
            "accuracy": _round_score(avg_accuracy),
            "activity": _round_score(activity_score),
            "collaboration": _round_score(avg_collaboration),
            "quality": _round_score(avg_quality),
            "stability": _round_score(stability_score),
            "completion": _round_score(completion_rate),
            "total": total_score,
        },
        "trends": {
            "total_delta": _round_score(total_score - previous_total),
            "accuracy_delta": _round_score(avg_accuracy - previous_accuracy),
            "efficiency_delta": _round_score(avg_efficiency - previous_efficiency),
        },
        "recent_tasks": [
            {
                "task_id": row.task_id,
                "project_id": row.project_id,
                "file_id": row.file_id,
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                "work_seconds": _round_score(row.work_seconds),
                "submitted_annotation_count": row.submitted_annotation_count,
                "reviewed_annotation_count": row.reviewed_annotation_count,
                "accuracy_score": _round_score(row.accuracy_score),
                "efficiency_score": _round_score(row.efficiency_score),
                "collaboration_score": _round_score(row.collaboration_score),
                "quality_score": _round_score(row.quality_score),
                "total_score": _round_score(row.total_score),
            }
            for row in recent_rows[:10]
        ],
    }


def bind_task_to_user(
    db: Session,
    task_id: str,
    user: User | None,
    task_row: dict[str, Any] | None = None,
) -> AnnotationTaskActivity:
    activity = _ensure_task_activity(db, task_id=task_id, task_row=task_row)
    _apply_user_binding(activity, user)
    if not activity.task_started_at:
        activity.task_started_at = _utc_now()
    db.commit()
    db.refresh(activity)
    return activity


def parse_tracker_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    tracker = payload.get("tracker") if isinstance(payload.get("tracker"), dict) else {}
    started_at = _parse_dt(tracker.get("started_at") or payload.get("started_at"))
    last_activity_at = _parse_dt(
        tracker.get("last_activity_at") or payload.get("last_activity_at")
    )
    work_seconds = tracker.get("work_seconds", payload.get("work_seconds"))
    save_count = tracker.get("save_count", payload.get("save_count"))
    try:
        work_seconds = float(work_seconds) if work_seconds is not None else None
    except (TypeError, ValueError):
        work_seconds = None
    try:
        save_count = int(save_count) if save_count is not None else None
    except (TypeError, ValueError):
        save_count = None
    return {
        "started_at": started_at,
        "last_activity_at": last_activity_at,
        "work_seconds": work_seconds,
        "save_count": save_count,
        "tracker": tracker,
    }
