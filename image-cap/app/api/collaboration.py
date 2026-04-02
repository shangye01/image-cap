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
    mode: str = Field(..., description="adopt_one | manual_edit | workbench_resolve | bulk_adopt_with_overrides")
    selected_annotator_id: str | None = None
    edited_annotations: list[BoxAnnotation] = Field(default_factory=list)
    cluster_decisions: list[dict[str, Any]] = Field(default_factory=list)
    base_annotator_id: str | None = None
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

    all_members: list[dict[str, Any]] = []
    for source_idx, anns in enumerate(submissions):
        for ann in anns:
            all_members.append({"source_idx": source_idx, "annotation": ann})

    clusters: list[dict[str, Any]] = []
    for member in all_members:
        source_idx = member["source_idx"]
        ann = member["annotation"]
        best_cluster_index = -1
        best_iou = 0.0
        for idx, cluster in enumerate(clusters):
            ious = [_iou(ann, m["annotation"]) for m in cluster["members"]]
            max_iou = max(ious) if ious else 0.0
            if max_iou >= align_iou_threshold and max_iou > best_iou:
                best_iou = max_iou
                best_cluster_index = idx

        if best_cluster_index >= 0:
            clusters[best_cluster_index]["members"].append(member)
            clusters[best_cluster_index]["source_indexes"].add(source_idx)
        else:
            clusters.append({"members": [member], "source_indexes": {source_idx}})

    return clusters


def _compute_annotator_dynamic_weights(submissions: list[list[dict[str, Any]]], iou_thr: float = 0.5) -> dict[int, float]:
    """动态权重：结合与其他标注员的匹配 IoU 和类别一致率。"""
    weights: dict[int, float] = {}
    n = len(submissions)
    for i in range(n):
        scores: list[float] = []
        for j in range(n):
            if i == j:
                continue
            pair_scores: list[float] = []
            for ann_i in submissions[i]:
                best = 0.0
                best_label_match = 0.0
                for ann_j in submissions[j]:
                    cur_iou = _iou(ann_i, ann_j)
                    if cur_iou > best:
                        best = cur_iou
                        best_label_match = 1.0 if ann_i.get("label") == ann_j.get("label") else 0.0
                if best >= iou_thr:
                    pair_scores.append(0.75 * best + 0.25 * best_label_match)
            if pair_scores:
                scores.append(sum(pair_scores) / len(pair_scores))
        # 下限 0.6，避免动态分被拉低后完全失语
        weights[i] = round(max(0.6, min(1.4, (sum(scores) / len(scores)) if scores else 0.8)), 4)
    return weights


def _fuse_cluster(cluster: dict[str, Any], annotator_weights: dict[int, float]) -> dict[str, Any]:
    members = cluster["members"]
    if not members:
        raise ValueError("cluster members 不能为空")

    static_annotator_weights = {0: 1.0, 1: 1.0, 2: 1.0}
    weighted_label_scores: Counter = Counter()
    weighted_sum = {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "score": 0.0}
    total_weight = 0.0

    normalized_members = []
    for member in members:
        ann = member["annotation"]
        source_idx = member["source_idx"]
        static_weight = static_annotator_weights.get(source_idx, 1.0)
        dynamic_weight = annotator_weights.get(source_idx, 1.0)
        confidence_weight = max(0.5, float(ann.get("score", 1.0)))
        member_weight = static_weight * dynamic_weight * confidence_weight
        total_weight += member_weight
        weighted_label_scores[ann["label"]] += member_weight
        weighted_sum["x"] += ann["x"] * member_weight
        weighted_sum["y"] += ann["y"] * member_weight
        weighted_sum["width"] += ann["width"] * member_weight
        weighted_sum["height"] += ann["height"] * member_weight
        weighted_sum["score"] += float(ann.get("score", 1.0)) * member_weight
        normalized_members.append({
            "annotator_index": source_idx,
            "annotation": ann,
            "weight": round(member_weight, 4),
        })

    top_label, top_weight = weighted_label_scores.most_common(1)[0]
    top_count = sum(1 for m in normalized_members if m["annotation"].get("label") == top_label)
    base = total_weight if total_weight > 0 else float(len(members))
    avg_x = weighted_sum["x"] / base
    avg_y = weighted_sum["y"] / base
    avg_w = weighted_sum["width"] / base
    avg_h = weighted_sum["height"] / base
    avg_score = weighted_sum["score"] / base

    pairwise = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            pairwise.append(_iou(members[i]["annotation"], members[j]["annotation"]))
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
            "label_vote_weighted": round(top_weight / max(1e-6, sum(weighted_label_scores.values())), 4),
            "mean_pairwise_iou": round(avg_pairwise_iou, 4),
            "member_count": len(members),
        },
        "_raw": normalized_members,
    }


def _build_difference_flags(cluster: dict[str, Any], fused: dict[str, Any], label_vote_threshold: int, iou_threshold: float) -> list[str]:
    flags: list[str] = []
    labels = [m["annotation"]["label"] for m in cluster["members"]]
    top = Counter(labels).most_common(1)[0][1]
    if top < label_vote_threshold:
        flags.append("类别不一致")

    if fused["agreement"]["mean_pairwise_iou"] < iou_threshold:
        flags.append("框位置IoU不一致")

    if len(cluster["members"]) < 3:
        flags.append("目标数量不一致")

    return flags


def _difference_type(cluster: dict[str, Any], fused: dict[str, Any], total_annotators: int) -> tuple[str | None, str | None]:
    members = cluster["members"]
    labels = [m["annotation"]["label"] for m in members]
    label_count = len(set(labels))
    mean_iou = fused["agreement"]["mean_pairwise_iou"]
    source_counts = Counter([m["source_idx"] for m in members])

    if any(v > 1 for v in source_counts.values()):
        return "over_segmentation", "合并框/删除冗余框"
    if len(source_counts) < total_annotators:
        return "missing_annotation", "确认是否保留漏标目标"
    if label_count > 1 and mean_iou >= 0.45:
        return "label_conflict", "单选裁决类别"
    if label_count == 1 and mean_iou < 0.75:
        return "bbox_minor_offset", "一键采用融合框/某标注员框"
    return None, None


def _consistency_score(cluster: dict[str, Any], fused: dict[str, Any]) -> float:
    """计算单个聚类的一致性分数（0~1）。"""
    members = cluster["members"]
    if not members:
        return 0.0

    labels = [m["annotation"]["label"] for m in members]
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
    annotator_index_map = {idx: aid for idx, aid in enumerate(ordered_annotators)}
    dynamic_weights = _compute_annotator_dynamic_weights(ordered_submissions, iou_thr=align_iou_threshold)
    clusters = _cluster_by_iou(ordered_submissions, align_iou_threshold=align_iou_threshold)

    fused_candidates: list[dict[str, Any]] = []
    difference_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    conflict_cluster_count = 0

    for cluster_idx, cluster in enumerate(clusters):
        fused = _fuse_cluster(cluster, annotator_weights=dynamic_weights)
        cluster_score = _consistency_score(cluster, fused)
        flags = _build_difference_flags(
            cluster,
            fused,
            label_vote_threshold=2,
            iou_threshold=consensus_iou_threshold,
        )
        diff_type, suggestion = _difference_type(cluster, fused, total_annotators=len(ordered_annotators))
        pass_auto = len(flags) == 0 and cluster_score >= 0.7

        member_overlays = []
        for m in fused["_raw"]:
            ann = m["annotation"]
            member_overlays.append({
                "annotator_index": m["annotator_index"],
                "annotator_id": annotator_index_map.get(m["annotator_index"]),
                "annotation_id": ann.get("id"),
                "label": ann.get("label"),
                "x": ann.get("x"),
                "y": ann.get("y"),
                "width": ann.get("width"),
                "height": ann.get("height"),
                "score": ann.get("score", 1.0),
                "fusion_weight": m["weight"],
            })

        difference_items.append(
            {
                "cluster_id": f"cluster_{cluster_idx}",
                "fused_id": fused["id"],
                "consistency_score": cluster_score,
                "pass_auto_merge": pass_auto,
                "flags": flags,
                "difference_type": diff_type,
                "review_suggestion": suggestion,
                "members": member_overlays,
                "fused_preview": {
                    k: fused[k]
                    for k in ["label", "x", "y", "width", "height", "agreement"]
                },
            }
        )

        if pass_auto:
            fused_candidates.append(fused)
        else:
            conflict_cluster_count += 1
            review_items.append(
                {
                    "cluster_id": f"cluster_{cluster_idx}",
                    "fused_id": fused["id"],
                    "consistency_score": cluster_score,
                    "flags": flags or ["一致性分数不足"],
                    "difference_type": diff_type or "cluster_conflict",
                    "review_suggestion": suggestion or "请人工裁决该冲突目标",
                    "quick_actions": [
                                         {"action": "adopt_annotator", "annotator_id": annotator_id}
                                         for annotator_id in ordered_annotators
                                     ] + [{"action": "adopt_fused"}],
                    "overlay": {
                        "member_boxes": member_overlays,
                        "fused_preview": {
                            k: fused[k]
                            for k in ["label", "x", "y", "width", "height", "agreement"]
                        },
                    },
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
    global_quantity_anomaly = quantity_spread >= 2

    # 存在未通过自动合并的簇，或数量跨度过大时，触发审核
    review_required = bool(review_items) or quantity_review_flag
    total_clusters = len(clusters)
    if conflict_cluster_count == 0 and not global_quantity_anomaly:
        integration_decision = "auto_pass"
    elif conflict_cluster_count <= max(2, total_clusters // 2) and not global_quantity_anomaly:
        integration_decision = "semi_auto_pass"
    else:
        integration_decision = "manual_full_review"

    for ann in final_annotations:
        ann.pop("_raw", None)

    return {
        "review_required": review_required,
        "auto_finalize": not review_required,
        "integration_decision": integration_decision,
        "integration_decision_text": {
            "auto_pass": "自动通过",
            "semi_auto_pass": "半自动通过",
            "manual_full_review": "人工全审",
        }.get(integration_decision, "人工全审"),
        "align_method": "IoU clustering",
        "align_iou_threshold": align_iou_threshold,
        "review_iou_threshold": review_iou_threshold,
        "consensus_iou_threshold": consensus_iou_threshold,
        "quantity_spread": quantity_spread,
        "quantity_review_flag": quantity_review_flag,
        "global_quantity_anomaly": global_quantity_anomaly,
        "annotator_weights_dynamic": {
            annotator_index_map[idx]: weight for idx, weight in dynamic_weights.items()
        },
        "annotator_order": ordered_annotators,
        "differences": difference_items,
        "review_queue": [item["cluster_id"] for item in review_items],
        "review_items": review_items,
        "review_workbench": {
            "conflict_only_mode_default": True,
            "batch_actions": [
                {"action": "adopt_all_from_annotator", "annotator_id": annotator_id}
                for annotator_id in ordered_annotators
            ],
        },
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

    if payload.mode not in {"adopt_one", "manual_edit", "workbench_resolve", "bulk_adopt_with_overrides"}:
        raise HTTPException(status_code=400,
                            detail="mode 仅支持 adopt_one / manual_edit / workbench_resolve / bulk_adopt_with_overrides")

    final_annotations: list[dict[str, Any]]

    if payload.mode == "adopt_one":
        if not payload.selected_annotator_id:
            raise HTTPException(status_code=400, detail="adopt_one 模式需要 selected_annotator_id")
        if payload.selected_annotator_id not in task["submissions"]:
            raise HTTPException(status_code=400, detail="selected_annotator_id 未提交标注")
        final_annotations = task["submissions"][payload.selected_annotator_id]
    elif payload.mode == "bulk_adopt_with_overrides":
        base_id = payload.base_annotator_id or payload.selected_annotator_id
        if not base_id:
            raise HTTPException(status_code=400, detail="bulk_adopt_with_overrides 需要 base_annotator_id")
        if base_id not in task["submissions"]:
            raise HTTPException(status_code=400, detail="base_annotator_id 未提交标注")
        final_annotations = list(task["submissions"][base_id])
        for decision in payload.cluster_decisions:
            if decision.get("action") == "replace_with_fused" and decision.get("fused_preview"):
                final_annotations.append(decision["fused_preview"])
            elif decision.get("action") == "replace_with_annotator":
                annotator_id = decision.get("annotator_id")
                if annotator_id in task["submissions"]:
                    final_annotations.extend(task["submissions"][annotator_id])
    elif payload.mode == "workbench_resolve":
        if not payload.cluster_decisions:
            raise HTTPException(status_code=400, detail="workbench_resolve 需要 cluster_decisions")
        final_annotations = list(task["consensus"].get("final_annotations") or [])
        for decision in payload.cluster_decisions:
            action = decision.get("action")
            if action == "adopt_fused" and decision.get("fused_preview"):
                final_annotations.append(decision["fused_preview"])
            elif action == "adopt_annotator":
                annotator_id = decision.get("annotator_id")
                cluster_annotation = decision.get("annotation")
                if annotator_id not in task["submissions"]:
                    continue
                if cluster_annotation:
                    final_annotations.append(cluster_annotation)
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