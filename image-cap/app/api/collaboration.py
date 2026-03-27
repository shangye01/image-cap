from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/collab", tags=["collaboration"])


class BoxAnnotation(BaseModel):
    id: str | None = None
    label: str
    x: float
    y: float
    width: float
    height: float
    score: float = 1.0


class ReplicateTaskRequest(BaseModel):
    task_id: str = Field(..., description="原始任务ID")
    image_url: str
    annotator_ids: list[str] = Field(..., min_length=3, max_length=3)


class SubmitAnnotationRequest(BaseModel):
    annotator_id: str
    annotations: list[BoxAnnotation] = Field(default_factory=list)


class ReviewDecisionRequest(BaseModel):
    reviewer_id: str
    mode: str = Field(..., description="adopt_one | manual_edit")
    selected_annotator_id: str | None = None
    edited_annotations: list[BoxAnnotation] = Field(default_factory=list)
    comment: str | None = None


@dataclass
class Assignment:
    assignment_id: str
    annotator_id: str


COLLAB_STORE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    x1 = max(a["x"], b["x"])
    y1 = max(a["y"], b["y"])
    x2 = min(a["x"] + a["width"], b["x"] + b["width"])
    y2 = min(a["y"] + a["height"], b["y"] + b["height"])
    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter = inter_w * inter_h
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union > 0 else 0.0


def _nms(boxes: list[dict[str, Any]], iou_thr: float = 0.55) -> list[dict[str, Any]]:
    sorted_boxes = sorted(boxes, key=lambda item: item.get("score", 1.0), reverse=True)
    kept: list[dict[str, Any]] = []
    while sorted_boxes:
        cur = sorted_boxes.pop(0)
        kept.append(cur)
        sorted_boxes = [
            b
            for b in sorted_boxes
            if b["label"] != cur["label"] or _iou(cur, b) < iou_thr
        ]
    return kept


def _cluster_by_iou(
    submissions: list[list[dict[str, Any]]],
    align_iou_threshold: float,
) -> list[dict[str, Any]]:
    if not submissions:
        return []

    clusters: list[dict[str, Any]] = []
    for ann in submissions[0]:
        clusters.append({"members": [ann], "source_indexes": {0}})

    for source_idx in range(1, len(submissions)):
        for ann in submissions[source_idx]:
            best_cluster_index = -1
            best_iou = 0.0
            for idx, cluster in enumerate(clusters):
                if source_idx in cluster["source_indexes"]:
                    continue
                ious = [_iou(ann, member) for member in cluster["members"]]
                max_iou = max(ious) if ious else 0.0
                if max_iou >= align_iou_threshold and max_iou > best_iou:
                    best_iou = max_iou
                    best_cluster_index = idx

            if best_cluster_index >= 0:
                clusters[best_cluster_index]["members"].append(ann)
                clusters[best_cluster_index]["source_indexes"].add(source_idx)
            else:
                clusters.append({"members": [ann], "source_indexes": {source_idx}})

    return clusters


def _fuse_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    members = cluster["members"]
    labels = [m["label"] for m in members]
    label_counter = Counter(labels)
    top_label, top_count = label_counter.most_common(1)[0]
    avg_x = sum(m["x"] for m in members) / len(members)
    avg_y = sum(m["y"] for m in members) / len(members)
    avg_w = sum(m["width"] for m in members) / len(members)
    avg_h = sum(m["height"] for m in members) / len(members)
    avg_score = sum(m.get("score", 1.0) for m in members) / len(members)

    pairwise = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            pairwise.append(_iou(members[i], members[j]))
    avg_pairwise_iou = sum(pairwise) / len(pairwise) if pairwise else 1.0

    return {
        "id": f"fused_{uuid.uuid4().hex[:8]}",
        "label": top_label,
        "x": round(avg_x, 2),
        "y": round(avg_y, 2),
        "width": round(avg_w, 2),
        "height": round(avg_h, 2),
        "score": round(avg_score, 4),
        "agreement": {
            "label_vote": f"{top_count}/{len(members)}",
            "mean_pairwise_iou": round(avg_pairwise_iou, 4),
            "member_count": len(members),
        },
        "_raw": members,
    }


def _build_difference_flags(cluster: dict[str, Any], fused: dict[str, Any], label_vote_threshold: int, iou_threshold: float) -> list[str]:
    flags: list[str] = []
    labels = [m["label"] for m in cluster["members"]]
    top = Counter(labels).most_common(1)[0][1]
    if top < label_vote_threshold:
        flags.append("类别不一致")

    if fused["agreement"]["mean_pairwise_iou"] < iou_threshold:
        flags.append("框位置IoU不一致")

    if len(cluster["members"]) < 3:
        flags.append("目标数量不一致")

    return flags


def _consistency_score(cluster: dict[str, Any], fused: dict[str, Any]) -> float:
    """计算单个聚类的一致性分数（0~1）。"""
    members = cluster["members"]
    if not members:
        return 0.0

    labels = [m["label"] for m in members]
    top_vote = Counter(labels).most_common(1)[0][1]
    label_ratio = top_vote / len(members)
    iou_score = fused["agreement"]["mean_pairwise_iou"]
    quantity_score = min(len(members), 3) / 3

    # 标签一致性权重更高，避免出现“2人person + 1人cat”时被少数标签带偏
    return round(0.5 * label_ratio + 0.35 * iou_score + 0.15 * quantity_score, 4)


def _run_consensus(
    submissions_by_annotator: dict[str, list[dict[str, Any]]],
    align_iou_threshold: float = 0.5,
    consensus_iou_threshold: float = 0.6,
    review_iou_threshold: float = 0.45,
) -> dict[str, Any]:
    ordered_annotators = list(submissions_by_annotator.keys())
    ordered_submissions = [submissions_by_annotator[a] for a in ordered_annotators]
    clusters = _cluster_by_iou(ordered_submissions, align_iou_threshold=align_iou_threshold)

    fused_candidates: list[dict[str, Any]] = []
    difference_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []

    for cluster in clusters:
        fused = _fuse_cluster(cluster)
        cluster_score = _consistency_score(cluster, fused)
        flags = _build_difference_flags(
            cluster,
            fused,
            label_vote_threshold=2,
            iou_threshold=consensus_iou_threshold,
        )
        pass_auto = len(flags) == 0 and cluster_score >= 0.7

        difference_items.append(
            {
                "fused_id": fused["id"],
                "consistency_score": cluster_score,
                "pass_auto_merge": pass_auto,
                "flags": flags,
                "members": cluster["members"],
                "fused_preview": {
                    k: fused[k]
                    for k in ["label", "x", "y", "width", "height", "agreement"]
                },
            }
        )

        if pass_auto:
            fused_candidates.append(fused)
        else:
            review_items.append(
                {
                    "fused_id": fused["id"],
                    "consistency_score": cluster_score,
                    "flags": flags or ["一致性分数不足"],
                    "fused_preview": {
                        k: fused[k]
                        for k in ["label", "x", "y", "width", "height", "agreement"]
                    },
                }
            )

    final_annotations = _nms(fused_candidates, iou_thr=0.55)

    # 数量级一致性检查：三位标注者数量跨度过大时触发审核
    counts = [len(v) for v in ordered_submissions]
    quantity_spread = max(counts) - min(counts) if counts else 0
    quantity_review_flag = quantity_spread > 1

    # 存在未通过自动合并的簇，或数量跨度过大时，触发审核
    review_required = bool(review_items) or quantity_review_flag

    for ann in final_annotations:
        ann.pop("_raw", None)

    return {
        "review_required": review_required,
        "auto_finalize": not review_required,
        "align_method": "IoU clustering",
        "align_iou_threshold": align_iou_threshold,
        "review_iou_threshold": review_iou_threshold,
        "consensus_iou_threshold": consensus_iou_threshold,
        "quantity_spread": quantity_spread,
        "quantity_review_flag": quantity_review_flag,
        "annotator_order": ordered_annotators,
        "differences": difference_items,
        "review_items": review_items,
        # 不再因为局部分歧清空最终结果；高一致性部分直接产出，分歧部分进入审核
        "final_annotations": final_annotations,
        "suggested_annotations": final_annotations,
    }


@router.post("/tasks/replicate")
def replicate_task(request: ReplicateTaskRequest):
    assignments: list[Assignment] = []
    for annotator_id in request.annotator_ids:
        assignments.append(
            Assignment(
                assignment_id=f"{request.task_id}__{annotator_id}__{uuid.uuid4().hex[:6]}",
                annotator_id=annotator_id,
            )
        )

    COLLAB_STORE[request.task_id] = {
        "task_id": request.task_id,
        "image_url": request.image_url,
        "annotator_ids": request.annotator_ids,
        "assignments": [a.__dict__ for a in assignments],
        "submissions": {},
        "status": "replicated",
        "created_at": _now(),
        "updated_at": _now(),
        "consensus": None,
        "review": None,
    }

    return {
        "task_id": request.task_id,
        "image_url": request.image_url,
        "assignments": [a.__dict__ for a in assignments],
        "message": "任务已复制为3份并分配给不同标注者",
    }


@router.post("/tasks/{task_id}/submit")
def submit_task_annotations(task_id: str, payload: SubmitAnnotationRequest):
    task = COLLAB_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="协作任务不存在，请先调用 /api/collab/tasks/replicate")

    if payload.annotator_id not in task["annotator_ids"]:
        raise HTTPException(status_code=400, detail="annotator_id 不在该任务分配名单中")

    task["submissions"][payload.annotator_id] = [ann.model_dump() for ann in payload.annotations]
    task["updated_at"] = _now()

    done_count = len(task["submissions"])
    all_done = done_count == 3

    response: dict[str, Any] = {
        "task_id": task_id,
        "received_from": payload.annotator_id,
        "received_count": len(payload.annotations),
        "submission_progress": f"{done_count}/3",
        "all_submissions_ready": all_done,
    }

    if all_done:
        consensus = _run_consensus(task["submissions"])
        task["consensus"] = consensus
        task["status"] = "review_required" if consensus["review_required"] else "auto_merged"
        response["consensus"] = consensus
        response["status"] = task["status"]

    return response


@router.get("/tasks/{task_id}/consensus")
def get_consensus(task_id: str):
    task = COLLAB_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="协作任务不存在")

    if not task.get("consensus"):
        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "尚未收齐3份标注，暂无法计算对齐与一致性",
            "submission_progress": f"{len(task['submissions'])}/3",
        }

    return {
        "task_id": task_id,
        "status": task["status"],
        "consensus": task["consensus"],
        "review": task.get("review"),
    }


@router.post("/tasks/{task_id}/review")
def review_consensus(task_id: str, payload: ReviewDecisionRequest):
    task = COLLAB_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="协作任务不存在")

    if not task.get("consensus"):
        raise HTTPException(status_code=400, detail="尚未产生一致性结果，不能审核")

    if payload.mode not in {"adopt_one", "manual_edit"}:
        raise HTTPException(status_code=400, detail="mode 仅支持 adopt_one 或 manual_edit")

    final_annotations: list[dict[str, Any]]

    if payload.mode == "adopt_one":
        if not payload.selected_annotator_id:
            raise HTTPException(status_code=400, detail="adopt_one 模式需要 selected_annotator_id")
        if payload.selected_annotator_id not in task["submissions"]:
            raise HTTPException(status_code=400, detail="selected_annotator_id 未提交标注")
        final_annotations = task["submissions"][payload.selected_annotator_id]
    else:
        final_annotations = [ann.model_dump() for ann in payload.edited_annotations]

    task["review"] = {
        "reviewer_id": payload.reviewer_id,
        "mode": payload.mode,
        "comment": payload.comment,
        "final_annotations": final_annotations,
        "reviewed_at": _now(),
    }
    task["status"] = "review_accepted"
    task["updated_at"] = _now()

    return {
        "task_id": task_id,
        "status": task["status"],
        "review": task["review"],
    }