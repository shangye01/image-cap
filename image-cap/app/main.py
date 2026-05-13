# main.py 第1行开始
import sys
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import traceback
import logging
import uuid
import json
import time
import shutil
import io
import threading
import re
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote
import numpy as np
import urllib.request
import torch
import hashlib
from redis import Redis

from pydantic import BaseModel
from typing import Optional
from PIL import Image
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query, Form, Depends, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from app.core.dataset_manager import dataset_manager
from .api import auth
from .api import performance
from .api import project_storage
from .api import collaboration
from .db.base import init_db
from app.core.dataset_manager import dataset_manager, DatasetManager, DatasetInfo
from .config import supabase, SUPABASE_URL, TRAINING_CONFIG
# 在 main.py 顶部添加
from app.core.auth_utils import _resolve_user_id_from_token, _resolve_ws_username
from app.schemas.project_storage import AnnotationSessionCreate, AnnotationSessionResponse, AnnotationSessionTask
from app.models import ProjectFile, Project
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dataset_routes import get_supabase_client, dataset_cache_manager
from app.api.project_storage import router as project_router
import uuid
from app.core.ws_manager import progress_ws_manager
from datetime import datetime
import logging
from fastapi.concurrency import run_in_threadpool
from app.api.dataset_routes import router as dataset_router
from app.models import User
from app.db.session import SessionLocal
from app.utils.jwt import ALGORITHM, SECRET_KEY
from app.services.user_performance import (
    bind_task_to_user,
    parse_tracker_payload,
    record_review_result,
    record_task_progress,
    record_task_started,
    record_task_submission,
)
from jose import jwt
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)
print(f"SUPABASE_URL: {SUPABASE_URL}")  # 加上这行看输出
app = FastAPI()

# 注册路由
app.include_router(dataset_router)
app.include_router(auth.router)
app.include_router(performance.router)
app.include_router(project_storage.router)
app.include_router(collaboration.router)

print("MAIN FILE:", __file__)
print("PROJECT_STORAGE FILE:", project_storage.__file__)

class ModelSwitchRequest(BaseModel):
    name: str


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    redis_client.ping()
    logger.info("Redis 缓存连接成功")
except Exception as exc:
    redis_client = None
    logger.warning(f"Redis 不可用，将跳过缓存: {exc}")


def _cache_get_json(key: str):
    if not redis_client:
        return None
    try:
        value = redis_client.get(key)
        if not value:
            return None
        return json.loads(value)
    except Exception as exc:
        logger.warning(f"读取 Redis 缓存失败 | key={key} | err={exc}")
        return None


def _cache_set_json(key: str, value: dict, ttl: int = 300):
    if not redis_client:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception as exc:
        logger.warning(f"写入 Redis 缓存失败 | key={key} | err={exc}")


def _cache_delete_pattern(pattern: str):
    if not redis_client:
        return
    try:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    except Exception as exc:
        logger.warning(f"删除 Redis 缓存失败 | pattern={pattern} | err={exc}")


def _make_cache_key(prefix: str, *parts) -> str:
    raw = ":".join(str(p) for p in parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"

def _load_task_annotations(task: dict[str, Any]) -> list[dict[str, Any]]:
    """统一读取任务标注（优先草稿，其次已提交标注）。"""
    task_id = task.get("id")
    if not task_id:
        return []

    if task.get("status") in {"completed", "reviewed"}:
        anns_result = supabase.table("annotations").select("*").eq("task_id", task_id).execute()
        anns = anns_result.data or [] if anns_result else []
        return [_normalize_annotation_box(ann) for ann in anns]

    draft_result = supabase.table("drafts").select("*").eq("task_id", task_id).maybe_single().execute()
    if draft_result and draft_result.data:
        draft_annotations = draft_result.data.get("annotations_json", [])
        return [_normalize_annotation_box(ann) for ann in draft_annotations]
    return []


def _get_project_lineage_context(project_id: str) -> dict[str, Any]:
    """解析项目与其共享副本关系，供协作标注跨副本聚合使用。"""
    try:
        project_uuid = uuid.UUID(str(project_id))
    except (TypeError, ValueError):
        return {
            "current_project_id": str(project_id or ""),
            "root_project_id": str(project_id or ""),
            "current_owner": "",
            "root_owner": "",
            "reviewer_id": None,
            "reviewer_username": None,
            "related_project_ids": [str(project_id)] if project_id else [],
            "reviewer_project_ids": [],
        }

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_uuid).first()
        if not project:
            return {
                "current_project_id": str(project_uuid),
                "root_project_id": str(project_uuid),
                "current_owner": "",
                "root_owner": "",
                "reviewer_id": None,
                "reviewer_username": None,
                "related_project_ids": [str(project_uuid)],
                "reviewer_project_ids": [],
            }

        root_project_id = project.source_project_id or project.id
        related_projects = (
            db.query(Project)
            .filter((Project.id == root_project_id) | (Project.source_project_id == root_project_id))
            .all()
        )
        if not related_projects:
            related_projects = [project]

        reviewer_username = None
        if project.reviewer_id:
            reviewer = db.query(User).filter(User.id == project.reviewer_id).first()
            if reviewer:
                reviewer_username = reviewer.username

        root_owner = project.owner_id
        for item in related_projects:
            if item.id == root_project_id:
                root_owner = item.owner_id
                break

        return {
            "current_project_id": str(project.id),
            "root_project_id": str(root_project_id),
            "current_owner": project.owner_id,
            "root_owner": root_owner,
            "reviewer_id": project.reviewer_id,
            "reviewer_username": reviewer_username,
            "related_project_ids": [str(item.id) for item in related_projects],
            "reviewer_project_ids": [
                str(item.id)
                for item in related_projects
                if reviewer_username and item.owner_id == reviewer_username
            ],
        }
    finally:
        db.close()


def _apply_collaboration_preview(
        task_obj: dict[str, Any],
        task: dict[str, Any],
        prefer_integrated_annotations: bool = False,
        include_collaboration_preview: bool = True,
) -> dict[str, Any]:
    """在任务响应中附加协作整合结果，审核视角优先展示整合后的预览。"""
    if not include_collaboration_preview:
        return task_obj

    try:
        integration = _collaborative_auto_integrate(task)
        if integration.get("ready"):
            task_obj["collaboration_integration"] = integration
            if prefer_integrated_annotations:
                task_obj["annotations"] = integration.get("fused_annotations") or []
                task_obj["annotation_source"] = "collaboration_fused"
    except Exception as integration_error:
        logger.warning(
            f"【COLLAB-PREVIEW】协作整合计算失败 | task_id={task.get('id')} | err={integration_error}"
        )
    return task_obj


def _task_sort_value(task: dict[str, Any]) -> str:
    return (
        task.get("reviewed_at")
        or task.get("updated_at")
        or task.get("completed_at")
        or task.get("created_at")
        or ""
    )


def _is_reviewer_workspace_owner(project_owner: str, lineage_context: dict[str, Any]) -> bool:
    reviewer_username = lineage_context.get("reviewer_username")
    return bool(project_owner and reviewer_username and project_owner == reviewer_username)


def _is_root_workspace_owner(project_owner: str, lineage_context: dict[str, Any]) -> bool:
    root_owner = lineage_context.get("root_owner")
    return bool(project_owner and root_owner and project_owner == root_owner)


def _requires_reviewed_result_for_root_owner(project_owner: str, lineage_context: dict[str, Any]) -> bool:
    reviewer_username = lineage_context.get("reviewer_username")
    return bool(
        reviewer_username
        and _is_root_workspace_owner(project_owner, lineage_context)
        and project_owner != reviewer_username
    )


def _should_prefer_reviewed_task(project_owner: str, lineage_context: dict[str, Any]) -> bool:
    return _is_reviewer_workspace_owner(
        project_owner, lineage_context
    ) or _requires_reviewed_result_for_root_owner(project_owner, lineage_context)


def _can_access_cross_project_annotations(project: Project | None, lineage_context: dict[str, Any]) -> bool:
    if not project:
        return False
    if _is_reviewer_workspace_owner(project.owner_id, lineage_context):
        return True
    if _is_root_workspace_owner(project.owner_id, lineage_context):
        related_ids = lineage_context.get("related_project_ids") or []
        return len(related_ids) > 1
    return False


def _pick_preferred_storage_task(
        storage_tasks: list[dict[str, Any]],
        prefer_reviewed: bool,
        reviewed_only: bool = False,
) -> dict[str, Any] | None:
    if not storage_tasks:
        return None

    ordered_tasks = sorted(storage_tasks, key=_task_sort_value, reverse=True)
    if prefer_reviewed:
        reviewed_task = next((task for task in ordered_tasks if task.get("status") == "reviewed"), None)
        if reviewed_task:
            return reviewed_task
        if reviewed_only:
            return None
    return ordered_tasks[0]


def _parse_annotator_index_from_base_source(base_source: Any) -> int | None:
    if not isinstance(base_source, str):
        return None
    source = base_source.strip()
    prefix = "annotator_"
    if not source.startswith(prefix):
        return None
    suffix = source[len(prefix):]
    if not suffix.isdigit():
        return None
    return int(suffix)


def _is_metric_task_eligible(
        task: dict[str, Any] | None,
        *,
        file_storage_path: str | None,
        lineage_context: dict[str, Any],
) -> bool:
    if not task:
        return False
    if file_storage_path and task.get("image_storage_path") != file_storage_path:
        return False

    related_project_ids = {
        str(project_id)
        for project_id in (lineage_context.get("related_project_ids") or [])
        if project_id
    }
    task_project_id = str(task.get("project_id") or "")
    if related_project_ids and task_project_id not in related_project_ids:
        return False

    task_status = str(task.get("status") or "").lower()
    return task_status in {"completed", "reviewed"}


def _resolve_metric_source_task_from_base_source(
        *,
        fallback_task: dict[str, Any],
        base_source: Any,
        lineage_context: dict[str, Any],
        file_storage_path: str | None,
        db: Session,
) -> dict[str, Any]:
    annotator_index = _parse_annotator_index_from_base_source(base_source)
    if annotator_index is None:
        return fallback_task

    image_storage_path = file_storage_path or fallback_task.get("image_storage_path")
    if not image_storage_path:
        return fallback_task

    related_project_ids = [
        str(project_id)
        for project_id in (lineage_context.get("related_project_ids") or [fallback_task.get("project_id")])
        if project_id
    ]
    if not related_project_ids:
        return fallback_task

    related_project_uuid_ids: list[uuid.UUID] = []
    for related_id in related_project_ids:
        try:
            related_project_uuid_ids.append(uuid.UUID(str(related_id)))
        except (TypeError, ValueError):
            continue

    project_owner_map: dict[str, str] = {}
    if related_project_uuid_ids:
        related_projects = (
            db.query(Project)
            .filter(Project.id.in_(related_project_uuid_ids))
            .all()
        )
        project_owner_map = {str(project.id): project.owner_id for project in related_projects}

    sibling_tasks_result = (
        supabase
        .table("tasks")
        .select("*")
        .in_("project_id", related_project_ids)
        .eq("image_storage_path", image_storage_path)
        .execute()
    )
    sibling_tasks = sibling_tasks_result.data or []
    if not sibling_tasks:
        return fallback_task

    excluded_owners = {
        lineage_context.get("root_owner"),
        lineage_context.get("reviewer_username"),
    }
    completed_siblings: list[dict[str, Any]] = []
    for sibling in sibling_tasks:
        sibling_status = str(sibling.get("status") or "").lower()
        if sibling_status != "completed":
            continue
        sibling_owner = project_owner_map.get(str(sibling.get("project_id")))
        if sibling_owner and sibling_owner in excluded_owners:
            continue
        completed_siblings.append(sibling)

    if not completed_siblings:
        return fallback_task

    completed_siblings.sort(key=_task_sort_value, reverse=True)
    latest_task_by_project: dict[str, dict[str, Any]] = {}
    for sibling in completed_siblings:
        sibling_project_id = str(sibling.get("project_id") or "")
        if sibling_project_id and sibling_project_id not in latest_task_by_project:
            latest_task_by_project[sibling_project_id] = sibling

    candidate_tasks = list(latest_task_by_project.values())
    if not candidate_tasks:
        return fallback_task

    candidate_tasks.sort(
        key=lambda item: (
            project_owner_map.get(str(item.get("project_id")), ""),
            str(item.get("project_id") or ""),
        )
    )
    if annotator_index < 0 or annotator_index >= len(candidate_tasks):
        return fallback_task

    selected_task = candidate_tasks[annotator_index]
    if not _is_metric_task_eligible(
            selected_task,
            file_storage_path=image_storage_path,
            lineage_context=lineage_context,
    ):
        return fallback_task
    return selected_task


def _resolve_user_id_from_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except Exception:
        return None


def _require_current_user(db: Session, authorization: str | None) -> User:
    user_id = _resolve_user_id_from_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或 token 无效")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _get_current_user_if_available(db: Session, authorization: str | None) -> User | None:
    user_id = _resolve_user_id_from_token(authorization)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def _resolve_ws_username(token: str | None) -> str | None:
    if not token:
        print("[WS_AUTH] Token 为空")
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"[WS_AUTH] Token 解码成功: {payload}")
        user_id = payload.get("user_id")
        if not user_id:
            print("[WS_AUTH] Token 缺少 user_id")
            return None

        # 检查是否过期（jwt.decode 应该会自动检查，但手动确认一下）
        exp = payload.get("exp")
        if exp and exp < time.time():
            print(f"[WS_AUTH] Token 已过期, exp={exp}, now={time.time()}")
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                print(f"[WS_AUTH] 找到用户: {user.username}")
                return user.username
            else:
                print(f"[WS_AUTH] 用户不存在: user_id={user_id}")
                return None
        finally:
            db.close()
    except jwt.ExpiredSignatureError:
        print("[WS_AUTH] JWT 过期异常")
        return None
    except jwt.JWTError as e:
        print(f"[WS_AUTH] JWT 错误: {e}")
        return None
    except Exception as e:
        print(f"[WS_AUTH] 未知错误: {e}")
        return None


@app.on_event("startup")
def _startup() -> None:
    init_db()
    try:
        auth.ensure_auth_resources()
    except Exception as exc:
        logger.warning(f"startup skipped auth storage bootstrap: {exc}")


@app.websocket("/api/ws/progress")
async def progress_websocket(websocket: WebSocket):
    # 先验证
    token = websocket.query_params.get("token")
    username = _resolve_ws_username(token)

    if not username:
        # 不 accept，让 FastAPI 返回 403
        from fastapi import WebSocketException, status
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    # 验证通过再 accept
    await websocket.accept()
    await progress_ws_manager.connect(username, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_ws_manager.disconnect(username, websocket)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        try:
            progress_ws_manager.disconnect(username, websocket)
            await websocket.close()
        except Exception:
            pass


# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== FastAPI 应用 ==========

def _get_allowed_origins() -> List[str]:
    """从环境变量读取允许跨域的来源，便于本地和局域网联调。"""
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    if not raw_origins:
        return default_origins

    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or default_origins


# CORS - 允许前端域名
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 本地目录 ==========
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_DIR = Path("./models")
MODEL_DIR.mkdir(exist_ok=True)
DATASET_DIR = Path("./datasets/custom")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_UPLOADS_BASE_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000").rstrip("/")

# 全局变量：存储最新训练结果
# 数据集注册表（用于内存缓存数据集状态，避免重复查询 Storage）
dataset_registry: dict[str, Any] = {}

latest_training_result = None

# ========== 颜色配置 ==========
CATEGORY_COLORS = {
    'vehicle': '#0000ff', 'car': '#0000ff', 'truck': '#0000ff',
    'bus': '#0000ff', 'motorcycle': '#0000ff', 'bicycle': '#0000ff',
    'animal': '#00ff00', 'dog': '#00ff00', 'cat': '#00ff00',
    'bird': '#00ff00', 'horse': '#00ff00', 'sheep': '#00ff00',
    'cow': '#00ff00', 'zebra': '#ffeb3b', 'giraffe': '#ff9800',
    'person': '#ff0000', 'people': '#ff0000',
    'traffic light': '#ffff00', 'stop sign': '#ff8800',
    'boat': '#00ffff', 'airplane': '#8800ff',
    'train': '#ff00ff', 'chair': '#ffaa00'
}
DEFAULT_COLOR = '#3b82f6'
ANNOTATIONS_OPTIONAL_COLUMNS = {"annotated_by", "color", "created_at", "confidence"}


# ========== 工具函数 ==========
def get_label_color(label: str) -> str:
    """根据标签名称获取颜色"""
    label_lower = label.lower()
    if label_lower in CATEGORY_COLORS:
        return CATEGORY_COLORS[label_lower]
    for keyword, color in CATEGORY_COLORS.items():
        if keyword in label_lower:
            return color
    return DEFAULT_COLOR


def _is_missing_schema_column(error: Exception, column_name: str) -> bool:
    message = str(error)
    return column_name in message and 'schema cache' in message


def _extract_missing_schema_column(error: Exception) -> Optional[str]:
    match = re.search(r"Could not find the '([^']+)' column", str(error))
    if match:
        return match.group(1)
    return None


def _strip_optional_annotation_columns(rows: List[Dict[str, Any]], columns: set[str] | None = None) -> List[Dict[str, Any]]:
    blocked_columns = columns or ANNOTATIONS_OPTIONAL_COLUMNS
    return [{key: value for key, value in row.items() if key not in blocked_columns} for row in rows]


def _insert_annotations_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    current_rows = rows
    stripped_columns = set()

    while True:
        try:
            supabase.table("annotations").insert(current_rows).execute()
            if stripped_columns:
                logger.warning("annotations 表兼容模式写入成功，已跳过字段: %s", sorted(stripped_columns))
            return
        except APIError as error:
            missing_column = _extract_missing_schema_column(error)
            if not missing_column or missing_column not in ANNOTATIONS_OPTIONAL_COLUMNS:
                raise

            if missing_column in stripped_columns:
                raise

            logger.warning("annotations 表缺少 %s 字段，使用兼容模式重试写入", missing_column)
            stripped_columns.add(missing_column)
            current_rows = _strip_optional_annotation_columns(current_rows, {missing_column})


def _delete_auto_fusion_annotations(task_id: str) -> None:
    try:
        supabase.table("annotations").delete().eq("task_id", task_id).eq("annotated_by", "auto_fusion").execute()
    except APIError as error:
        if _is_missing_schema_column(error, "annotated_by"):
            logger.warning("annotations 表缺少 annotated_by 字段，兼容模式下删除 task_id=%s 的已有整合标注", task_id)
            supabase.table("annotations").delete().eq("task_id", task_id).execute()
            return
        raise


def calculate_iou(box1: Dict[str, float], box2: Dict[str, float]) -> float:
    """计算两个框的 IOU"""
    x1 = max(box1['x'], box2['x'])
    y1 = max(box1['y'], box2['y'])
    x2 = min(box1['x'] + box1['width'], box2['x'] + box2['width'])
    y2 = min(box1['y'] + box1['height'], box2['y'] + box2['height'])
    intersection_width = max(0, x2 - x1)
    intersection_height = max(0, y2 - y1)
    intersection = intersection_width * intersection_height
    area1 = box1['width'] * box1['height']
    area2 = box2['width'] * box2['height']
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0


def remove_duplicate_annotations(annotations: List[Dict[str, Any]], iou_threshold: float = 0.85) -> List[
    Dict[str, Any]]:
    """移除重叠的标注框"""
    if not annotations or len(annotations) <= 1:
        return annotations
    sorted_anns = sorted(annotations, key=lambda x: x.get('confidence', 0), reverse=True)
    keep = []
    suppressed = set()
    for i, current in enumerate(sorted_anns):
        if i in suppressed:
            continue
        keep.append(current)
        for j in range(i + 1, len(sorted_anns)):
            if j in suppressed:
                continue
            other = sorted_anns[j]
            iou = calculate_iou(current, other)
            if iou > iou_threshold:
                suppressed.add(j)
    return keep


def _normalize_annotation_box(annotation: Dict[str, Any]) -> Dict[str, Any]:
    """标准化标注框字段，兼容 drafts/annotations 两种来源。"""
    return {
        "id": annotation.get("id", f"ann_{uuid.uuid4().hex[:8]}"),
        "label": str(annotation.get("label", "object")),
        "x": float(annotation.get("x", 0)),
        "y": float(annotation.get("y", 0)),
        "width": float(annotation.get("width", 0)),
        "height": float(annotation.get("height", 0)),
        "confidence": float(annotation.get("confidence", 1.0)),
        "color": annotation.get("color", DEFAULT_COLOR),
    }


def _build_iou_matches(base_annotations: List[Dict[str, Any]],
                       other_annotations: List[Dict[str, Any]],
                       iou_threshold: float) -> List[Tuple[int, int, float]]:
    """
    基于 IOU 的一对一贪心匹配（替代 Hungarian，满足“选其一即可”）。
    返回 (base_idx, other_idx, iou) 列表。
    """
    candidate_pairs: list[tuple[int, int, float]] = []
    for i, base_ann in enumerate(base_annotations):
        for j, other_ann in enumerate(other_annotations):
            if base_ann.get("label") != other_ann.get("label"):
                continue
            iou = calculate_iou(base_ann, other_ann)
            if iou >= iou_threshold:
                candidate_pairs.append((i, j, iou))

    candidate_pairs.sort(key=lambda item: item[2], reverse=True)
    used_base: set[int] = set()
    used_other: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for i, j, iou in candidate_pairs:
        if i in used_base or j in used_other:
            continue
        used_base.add(i)
        used_other.add(j)
        matches.append((i, j, iou))
    return matches


def _fuse_matched_annotations(matched_annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对同一目标的多份标注进行融合（均值 + 最大置信度），后续再执行 NMS。"""
    if not matched_annotations:
        raise ValueError("matched_annotations 不能为空")

    labels = [ann.get("label", "object") for ann in matched_annotations]
    majority_label = max(set(labels), key=labels.count)
    return {
        "id": f"auto_{uuid.uuid4().hex[:10]}",
        "label": majority_label,
        "x": round(sum(ann.get("x", 0) for ann in matched_annotations) / len(matched_annotations), 2),
        "y": round(sum(ann.get("y", 0) for ann in matched_annotations) / len(matched_annotations), 2),
        "width": round(sum(ann.get("width", 0) for ann in matched_annotations) / len(matched_annotations), 2),
        "height": round(sum(ann.get("height", 0) for ann in matched_annotations) / len(matched_annotations), 2),
        "confidence": round(max(float(ann.get("confidence", 1.0)) for ann in matched_annotations), 3),
        "color": get_label_color(majority_label),
    }


def _cluster_annotations_globally(annotation_sets: List[List[Dict[str, Any]]],
                                  iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """不依赖参考标注的全局聚类：按空间 IoU 将多标注结果聚成目标簇。"""
    normalized_members: list[dict[str, Any]] = []
    for annotator_idx, ann_list in enumerate(annotation_sets):
        for ann in ann_list:
            normalized_members.append({
                "annotator_idx": annotator_idx,
                "annotation": ann
            })

    clusters: list[dict[str, Any]] = []
    for member in normalized_members:
        ann = member["annotation"]
        best_idx = -1
        best_iou = 0.0
        for idx, cluster in enumerate(clusters):
            ious = [calculate_iou(ann, m["annotation"]) for m in cluster["members"]]
            cluster_max_iou = max(ious) if ious else 0.0
            if cluster_max_iou >= iou_threshold and cluster_max_iou > best_iou:
                best_idx = idx
                best_iou = cluster_max_iou
        if best_idx >= 0:
            clusters[best_idx]["members"].append(member)
        else:
            clusters.append({"members": [member]})
    return clusters


def _summarize_cluster(cluster: Dict[str, Any], total_annotators: int) -> Dict[str, Any]:
    members = cluster.get("members", [])
    labels = [m["annotation"].get("label", "object") for m in members]
    label_counter = Counter(labels)
    dominant_label, dominant_count = label_counter.most_common(1)[0]
    label_vote_ratio = round(dominant_count / max(1, len(members)), 3)

    x_values = [m["annotation"].get("x", 0) for m in members]
    y_values = [m["annotation"].get("y", 0) for m in members]
    w_values = [m["annotation"].get("width", 0) for m in members]
    h_values = [m["annotation"].get("height", 0) for m in members]
    center_box = {
        "x": round(sum(x_values) / max(1, len(x_values)), 2),
        "y": round(sum(y_values) / max(1, len(y_values)), 2),
        "width": round(sum(w_values) / max(1, len(w_values)), 2),
        "height": round(sum(h_values) / max(1, len(h_values)), 2),
    }

    pairwise_ious: list[float] = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            pairwise_ious.append(calculate_iou(members[i]["annotation"], members[j]["annotation"]))
    max_iou = round(max(pairwise_ious), 3) if pairwise_ious else 1.0
    min_iou = round(min(pairwise_ious), 3) if pairwise_ious else 1.0
    mean_iou = round(sum(pairwise_ious) / len(pairwise_ious), 3) if pairwise_ious else 1.0

    annotator_indexes = [m["annotator_idx"] for m in members]
    annotator_counter = Counter(annotator_indexes)
    annotator_set = sorted({idx for idx in annotator_indexes})
    full_participation = len(annotator_set) == total_annotators
    two_vs_one_pattern = full_participation and dominant_count == 2
    oversegmented = any(count > 1 for count in annotator_counter.values())

    return {
        "members": members,
        "member_count": len(members),
        "annotators": annotator_set,
        "annotator_count": len(annotator_set),
        "annotator_counter": {str(k): v for k, v in annotator_counter.items()},
        "labels": dict(label_counter),
        "dominant_label": dominant_label,
        "label_vote_ratio": label_vote_ratio,
        "center_box": center_box,
        "box_deviations": [
            {
                "annotation_id": m["annotation"].get("id"),
                "annotator_idx": m["annotator_idx"],
                "dx": round(abs(m["annotation"].get("x", 0) - center_box["x"]), 2),
                "dy": round(abs(m["annotation"].get("y", 0) - center_box["y"]), 2),
                "dw": round(abs(m["annotation"].get("width", 0) - center_box["width"]), 2),
                "dh": round(abs(m["annotation"].get("height", 0) - center_box["height"]), 2),
            }
            for m in members
        ],
        "iou_stats": {
            "max_iou": max_iou,
            "min_iou": min_iou,
            "mean_iou": mean_iou
        },
        "full_participation": full_participation,
        "two_vs_one_pattern": two_vs_one_pattern,
        "oversegmented": oversegmented,
    }


def _classify_cluster_difference(cluster_summary: Dict[str, Any]) -> Tuple[str | None, str | None]:
    """差异分级：类别冲突 / 边框轻微偏移 / 漏标 / 重标过分割。"""
    full_participation = cluster_summary["full_participation"]
    label_count = len(cluster_summary["labels"])
    mean_iou = cluster_summary["iou_stats"]["mean_iou"]
    min_iou = cluster_summary["iou_stats"]["min_iou"]

    if cluster_summary["oversegmented"]:
        return "over_segmentation", "建议合并框或删除冗余框"

    if not full_participation:
        return "missing_annotation", "建议确认是否保留该目标"

    if label_count > 1 and mean_iou >= 0.45:
        return "label_conflict", "建议单选裁决目标类别"

    if label_count == 1 and 0.35 <= mean_iou < 0.75 and min_iou >= 0.2:
        return "bbox_minor_offset", "建议一键采用均值框或指定标注员框"

    return None, None


def _collaborative_auto_integrate(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    协作标注自动整合：
    1) 汇总同图像的三份标注
    2) 基于全局 IoU 聚类对齐目标（不依赖参考标注）
    3) 按差异类型分级并生成审核建议
    4) 输出三段式整合判定：自动通过 / 半自动通过 / 人工全审
    """
    image_storage_path = task.get("image_storage_path")
    project_id = task.get("project_id")
    if not image_storage_path or not project_id:
        return {"ready": False, "reason": "任务缺少 image_storage_path 或 project_id"}

    lineage_context = _get_project_lineage_context(project_id)
    related_project_ids = lineage_context.get("related_project_ids") or [str(project_id)]
    project_owner_map: dict[str, str] = {}
    related_project_uuid_ids = []
    for related_id in related_project_ids:
        try:
            related_project_uuid_ids.append(uuid.UUID(str(related_id)))
        except (TypeError, ValueError):
            continue

    db = SessionLocal()
    try:
        related_projects = (
            db.query(Project)
            .filter(Project.id.in_(related_project_uuid_ids))
            .all()
            if related_project_uuid_ids
            else []
        )
        project_owner_map = {str(project.id): project.owner_id for project in related_projects}
    finally:
        db.close()

    sibling_tasks_result = (
        supabase
        .table("tasks")
        .select("*")
        .in_("project_id", related_project_ids)
        .eq("image_storage_path", image_storage_path)
        .execute()
    )
    sibling_tasks = sibling_tasks_result.data or []
    if len(sibling_tasks) < 3:
        return {"ready": False, "reason": "同图像任务不足 3 份"}

    excluded_owners = {
        lineage_context.get("root_owner"),
        lineage_context.get("reviewer_username"),
    }
    candidate_siblings = []
    for sibling in sibling_tasks:
        sibling_owner = project_owner_map.get(str(sibling.get("project_id")))
        if sibling_owner and sibling_owner in excluded_owners:
            continue
        candidate_siblings.append(sibling)

    completed_siblings = [t for t in candidate_siblings if t.get("status") == "completed"]
    if len(completed_siblings) < 3:
        return {"ready": False, "reason": "尚未收齐 3 份已提交标注"}

    completed_siblings.sort(key=_task_sort_value, reverse=True)

    latest_task_by_project: dict[str, dict[str, Any]] = {}
    for sibling in completed_siblings:
        sibling_project_id = str(sibling.get("project_id") or "")
        if sibling_project_id and sibling_project_id not in latest_task_by_project:
            latest_task_by_project[sibling_project_id] = sibling

    unique_completed_siblings = list(latest_task_by_project.values())
    if len(unique_completed_siblings) < 3:
        return {"ready": False, "reason": "有效标注员结果不足 3 份"}

    unique_completed_siblings.sort(
        key=lambda item: (
            project_owner_map.get(str(item.get("project_id")), ""),
            str(item.get("project_id") or ""),
        )
    )
    selected_tasks = unique_completed_siblings[:3]

    annotation_sets: list[list[dict[str, Any]]] = []
    source_task_ids: list[str] = []
    annotator_entries: list[dict[str, Any]] = []
    for idx, sibling in enumerate(selected_tasks):
        sibling_task_id = sibling.get("id")
        source_task_ids.append(sibling_task_id)
        sibling_anns_res = supabase.table("annotations").select("*").eq("task_id", sibling_task_id).execute()
        sibling_anns = sibling_anns_res.data or []
        normalized_annotations = [_normalize_annotation_box(ann) for ann in sibling_anns]
        annotation_sets.append(normalized_annotations)
        annotator_entries.append(
            {
                "annotator_index": idx,
                "annotator_label": f"标注员 {['A', 'B', 'C'][idx] if idx < 3 else idx + 1}",
                "owner_id": project_owner_map.get(str(sibling.get("project_id")), ""),
                "project_id": sibling.get("project_id"),
                "task_id": sibling_task_id,
                "annotations": normalized_annotations,
            }
        )

    if any(len(anns) == 0 for anns in annotation_sets):
        return {"ready": False, "reason": "存在空标注结果，无法自动整合"}

    count_values = [len(anns) for anns in annotation_sets]
    count_spread = max(count_values) - min(count_values)
    count_consistent = count_spread <= 1
    global_quantity_anomaly = count_spread >= 2

    raw_clusters = _cluster_annotations_globally(annotation_sets, iou_threshold=0.5)
    cluster_summaries = [_summarize_cluster(cluster, total_annotators=3) for cluster in raw_clusters]
    cluster_summaries.sort(key=lambda item: item["member_count"], reverse=True)

    review_items: list[dict[str, Any]] = []
    fused_annotations: list[dict[str, Any]] = []
    auto_pass_clusters = 0
    unresolved_conflict_count = 0

    for idx, summary in enumerate(cluster_summaries):
        diff_type, recommendation = _classify_cluster_difference(summary)
        has_full_participation = summary["full_participation"]
        is_high_consensus = (
                has_full_participation
                and len(summary["labels"]) == 1
                and summary["iou_stats"]["mean_iou"] >= 0.75
                and summary["iou_stats"]["min_iou"] >= 0.55
                and not summary["oversegmented"]
        )

        if is_high_consensus:
            auto_pass_clusters += 1
            matched_annotations = [member["annotation"] for member in summary["members"]]
            fused_annotations.append(_fuse_matched_annotations(matched_annotations))
            continue

            # 半自动可直接融合：2 人一致 + 空间接近，保留冲突供审核
        is_semi_auto_mergeable = (
                summary["label_vote_ratio"] >= 0.67
                and summary["iou_stats"]["mean_iou"] >= 0.5
                and not summary["oversegmented"]
        )
        if is_semi_auto_mergeable:
            dominant_label = summary["dominant_label"]
            dominant_members = [
                member["annotation"] for member in summary["members"]
                if member["annotation"].get("label") == dominant_label
            ]
            if dominant_members:
                fused_annotations.append(_fuse_matched_annotations(dominant_members))

        if diff_type:
            if not is_semi_auto_mergeable:
                unresolved_conflict_count += 1
            overlay_member_boxes = [
                {
                    "annotator_index": member["annotator_idx"],
                    "annotation_id": member["annotation"].get("id"),
                    "label": member["annotation"].get("label"),
                    "x": member["annotation"].get("x"),
                    "y": member["annotation"].get("y"),
                    "width": member["annotation"].get("width"),
                    "height": member["annotation"].get("height"),
                    "confidence": member["annotation"].get("confidence", 1.0),
                    "color": member["annotation"].get("color", DEFAULT_COLOR),
                }
                for member in summary["members"]
            ]
            review_items.append({
                "cluster_index": idx,
                "difference_type": diff_type,
                "recommended_action": recommendation,
                "quick_actions": [
                    {"action": "adopt_annotator", "annotator_index": 0},
                    {"action": "adopt_annotator", "annotator_index": 1},
                    {"action": "adopt_annotator", "annotator_index": 2},
                    {"action": "adopt_fused"},
                ],
                "overlay": {
                    "member_boxes": overlay_member_boxes,
                    "fused_preview": _fuse_matched_annotations(
                        [member["annotation"] for member in summary["members"]]
                    ),
                },
                "cluster_snapshot": {
                    "member_count": summary["member_count"],
                    "annotators": summary["annotators"],
                    "label_votes": summary["labels"],
                    "label_vote_ratio": summary["label_vote_ratio"],
                    "center_box": summary["center_box"],
                    "iou_stats": summary["iou_stats"],
                    "oversegmented": summary["oversegmented"],
                    "two_vs_one_pattern": summary["two_vs_one_pattern"],
                    "annotator_counter": summary["annotator_counter"],
                    "box_deviations": summary["box_deviations"],
                }
            })

    fused_annotations = remove_duplicate_annotations(fused_annotations, iou_threshold=0.7)

    semi_auto_conflict_count = len(review_items)
    total_clusters = len(cluster_summaries)
    review_rules: list[str] = []
    if global_quantity_anomaly:
        review_rules.append("全局数量异常：三份标注目标数差距较大")

    if auto_pass_clusters == total_clusters and not global_quantity_anomaly:
        integration_decision = "auto_pass"
    elif (
            not global_quantity_anomaly
            and semi_auto_conflict_count <= max(2, total_clusters // 2)
            and unresolved_conflict_count == 0
    ):
        integration_decision = "semi_auto_pass"
    else:
        integration_decision = "manual_full_review"

    review_triggered = integration_decision == "manual_full_review"
    auto_integrated = integration_decision in {"auto_pass", "semi_auto_pass"}
    if review_triggered:
        review_rules.append("存在需人工处理的差异簇")
    elif semi_auto_conflict_count:
        review_rules.append("存在轻微差异，系统已自动融合")
    consistency_ratio = round(auto_pass_clusters / max(1, total_clusters), 3)

    return {
        "ready": True,
        "source_task_ids": source_task_ids,
        "count_consistent": count_consistent,
        "count_spread": count_spread,
        "global_quantity_anomaly": global_quantity_anomaly,
        "unresolved_conflict_count": unresolved_conflict_count,
        "consistency_ratio": consistency_ratio,
        "align_method": "global_iou_clustering",
        "integration_decision": integration_decision,
        "integration_decision_text": {
            "auto_pass": "自动通过",
            "semi_auto_pass": "半自动通过",
            "manual_full_review": "人工全审"
        }.get(integration_decision, "人工全审"),
        "cluster_details": [
            {
                "member_count": summary["member_count"],
                "annotators": summary["annotators"],
                "labels": summary["labels"],
                "label_vote_ratio": summary["label_vote_ratio"],
                "center_box": summary["center_box"],
                "iou_stats": summary["iou_stats"],
                "full_participation": summary["full_participation"],
                "two_vs_one_pattern": summary["two_vs_one_pattern"],
                "oversegmented": summary["oversegmented"],
                "annotator_counter": summary["annotator_counter"],
                "box_deviations": summary["box_deviations"],
            }
            for summary in cluster_summaries
        ],
        "diff_highlights": review_items,
        "review_triggered": review_triggered,
        "review_rules": review_rules,
        "review_queue": [item["cluster_index"] for item in review_items],
        "review_workbench": {
            "conflict_only_mode_default": True,
            "batch_actions": [
                {"action": "adopt_all_from_annotator", "annotator_index": 0},
                {"action": "adopt_all_from_annotator", "annotator_index": 1},
                {"action": "adopt_all_from_annotator", "annotator_index": 2},
                {"action": "adopt_fused_as_default"},
            ],
        },
        "annotator_entries": annotator_entries,
        "auto_integrated": auto_integrated,
        "fused_annotations": fused_annotations,
    }


def build_local_upload_url(filename: str, request: Optional[Request] = None) -> str:
    """构建本地上传图片地址，优先使用当前请求域名。"""
    safe_filename = quote(filename)
    if request:
        return str(request.url_for("get_local_upload", filename=safe_filename))
    return f"{LOCAL_UPLOADS_BASE_URL}/local-uploads/{safe_filename}"


# ========== 数据集验证器 ==========
class DatasetValidator:
    """数据集验证器"""

    @staticmethod
    def validate(dataset_dir: Path = None) -> Tuple[bool, str, Dict]:
        """验证数据集"""
        # 如果传入路径，使用传入路径；否则使用默认路径
        base_dir = dataset_dir or DATASET_DIR

        train_images = base_dir / "train" / "images"
        train_labels = base_dir / "train" / "labels"
        val_images = base_dir / "val" / "images"
        val_labels = base_dir / "val" / "labels"

        errors = []
        stats = {}

        for path, name in [(train_images, "训练图片"), (train_labels, "训练标注"),
                           (val_images, "验证图片"), (val_labels, "验证标注")]:
            if not path.exists():
                errors.append(f"{name}目录不存在")

        if errors:
            return False, "目录结构不完整", {"errors": errors}

        train_count = len(list(train_images.glob("*")))
        val_count = len(list(val_images.glob("*")))
        stats = {"train": train_count, "val": val_count}

        if train_count < 10:
            errors.append(f"训练集太少 ({train_count} < 10)")

        return len(errors) == 0, "验证通过" if not errors else "数据不足", {
            "stats": stats,
            "errors": errors
        }


# ========== 模型管理器 ==========
class ModelManager:
    MODEL_SIZES = {'n': 'yolov8n.pt', 's': 'yolov8s.pt', 'm': 'yolov8m.pt', 'l': 'yolov8l.pt', 'x': 'yolov8x.pt'}

    def __init__(self):
        self.current_model = None
        self.active_version = "yolov8n"
        self.model_size = 'n'
        self.load_model()

    def select_size(self, train_count: int) -> str:
        """根据数据量选择模型"""
        if train_count < 100:
            return 'n'
        elif train_count < 500:
            return 's'
        elif train_count < 2000:
            return 'm'
        elif train_count < 10000:
            return 'l'
        return 'x'

    def load_model(self, path: Optional[str] = None):
        if path and os.path.exists(path):
            self.current_model = YOLO(path)
            self.active_version = Path(path).stem
        else:
            custom = sorted(MODEL_DIR.glob("*.pt"), key=lambda p: p.stat().st_mtime, reverse=True)
            if custom:
                self.current_model = YOLO(str(custom[0]))
                self.active_version = custom[0].stem
            else:
                self.current_model = YOLO("yolov8n.pt")
                self.active_version = "yolov8n"

    def get(self):
        return self.current_model, self.active_version

    def switch(self, path: str, name: str):
        self.current_model = YOLO(path)
        self.active_version = name


model_manager = ModelManager()


# ========== 训练相关函数 ==========
def run_training(
        project_id: str,
        dataset_id: str,
        epochs: int,
        batch: int,
        model_size: str,
        use_aug: bool,
        optimizer: str = 'AdamW',
        lr0: float = 0.001,
        imgsz: int = 640,
        patience: int = 20,
        weight_decay: float = 0.0005,
        dropout: float = 0.0,
        label_smoothing: float = 0.0,
        freeze: int = 0,
        warmup_epochs: int = 3,
        mosaic: float = 1.0,
        mixup: float = 0.1,
        copy_paste: float = 0.0,
        degrees: float = 15.0,
        scale: float = 0.5,
        shear: float = 5.0
):
    """执行训练（后台任务）"""
    global latest_training_result
    start_time = time.time()

    # 获取数据集路径
    cache_path = dataset_manager.get_cache_path(dataset_id)

    if not cache_path or not cache_path.exists():
        logger.error(f"数据集缓存不存在: {dataset_id}")
        latest_training_result = None
        return

    try:
        logger.info("=" * 60)
        logger.info(f"🚀 开始训练 | 数据集: {dataset_id} | 轮数: {epochs} | 批次: {batch} | 图片尺寸: {imgsz}")
        logger.info(f"⚙️  优化器: {optimizer} | 学习率: {lr0} | 冻结层: {freeze}")
        logger.info(f"📁 数据集路径: {cache_path}")

        # 使用数据集目录生成 yaml
        yaml_path = prepare_yaml(cache_path)
        train_count = len(list((cache_path / "train" / "images").glob("*")))

        base_model = find_latest_custom_model() or ModelManager.MODEL_SIZES.get(model_size, 'yolov8n.pt')

        if base_model != ModelManager.MODEL_SIZES.get(model_size, 'yolov8n.pt'):
            logger.info(f"🔄 使用上次训练的模型继续训练: {Path(base_model).name}")
        else:
            logger.info(f"🆕 使用预训练模型开始新训练: {base_model}")

        version = generate_version_name()
        logger.info(f"📋 模型版本: {version}")

        model = YOLO(base_model)

        # 构建训练参数
        args = {
            "data": yaml_path,
            "epochs": epochs,
            "batch": batch,
            "imgsz": imgsz,
            "name": version,
            "project": "runs/train",
            "exist_ok": True,
            "patience": patience,
            "save": True,
            "amp": True,
            "optimizer": optimizer,
            "lr0": lr0,
            "lrf": 0.01,
            "momentum": 0.937,
            "weight_decay": weight_decay,
            "warmup_epochs": warmup_epochs,
            "dropout": dropout,
            "label_smoothing": label_smoothing,
        }

        if freeze > 0:
            args["freeze"] = freeze
            logger.info(f"🧊 冻结前 {freeze} 层网络")

        if use_aug:
            args.update({
                "degrees": degrees,
                "translate": 0.1,
                "scale": scale,
                "shear": shear,
                "flipud": 0.5,
                "fliplr": 0.5,
                "hsv_h": 0.015,
                "hsv_s": 0.7,
                "hsv_v": 0.4,
                "mosaic": mosaic,
                "mixup": mixup,
                "copy_paste": copy_paste,
            })

        # 数据量少的特殊处理
        if train_count < 200 and epochs > 20 and base_model.endswith('.pt') and 'custom' not in base_model:
            if freeze == 0:
                logger.info("🔒 阶段1: 冻结主干网络预热...")
                model.train(**{**args, "epochs": min(10, epochs // 5), "freeze": 10, "lr0": lr0 * 0.5})
                logger.info("🔓 解冻继续训练...")
                args.pop("freeze", None)

        # 执行主训练
        results = model.train(**args)

        # 保存模型（与之前相同）
        best_pt = Path(f"runs/train/{version}/weights/best.pt")
        if not best_pt.exists():
            raise FileNotFoundError("未找到训练好的模型文件")

        target = MODEL_DIR / f"{version}.pt"
        shutil.copy(best_pt, target)
        logger.info(f"✅ 模型已保存到本地: {target}")

        best_link = MODEL_DIR / "best.pt"
        shutil.copy(best_pt, best_link)
        logger.info(f"✅ 已更新 best.pt")

        save_training_info(version, target, results, base_model)

        metrics = {
            "map50": float(results.results_dict.get('metrics/mAP50(B)', 0)),
            "map75": float(results.results_dict.get('metrics/mAP75(B)', 0)),
            "map50_95": float(results.results_dict.get('metrics/mAP50-95(B)', 0)),
            "precision": float(results.results_dict.get('metrics/precision(B)', 0)),
            "recall": float(results.results_dict.get('metrics/recall(B)', 0)),
        }

        # 保存到数据库
        try:
            supabase.table("model_versions").update({"is_active": False}).neq("id", 0).execute()

            db_result = supabase.table("model_versions").insert({
                "version_name": version,
                "training_data_count": train_count,
                "dataset_id": dataset_id,
                "model_size": model_size,
                "imgsz": imgsz,
                "optimizer": optimizer,
                "lr0": lr0,
                "batch": batch,
                "epochs": epochs,
                **metrics,
                "model_path": None,
                "local_path": str(target.absolute()),
                "is_active": True,
                "training_status": "completed",
                "completed_at": datetime.now().isoformat()
            }).execute()

            db_id = db_result.data[0]["id"] if db_result.data else None

        except Exception as db_err:
            logger.warning(f"数据库更新失败: {db_err}")
            db_id = None

        model_manager.switch(str(target), version)

        training_duration = (time.time() - start_time) / 3600

        latest_training_result = {
            "id": db_id,
            "version_name": version,
            "dataset_id": dataset_id,
            "local_path": str(target.absolute()),
            "metrics": metrics,
            "uploaded": False,
            "completed_at": datetime.now().isoformat(),
            "duration_hours": training_duration,
            "config": {
                "epochs": epochs,
                "batch": batch,
                "imgsz": imgsz,
                "optimizer": optimizer,
                "lr0": lr0,
                "model_size": model_size
            }
        }

        logger.info("=" * 60)
        logger.info(f"✅ 训练完成: {version}")
        logger.info(f"📊 mAP50: {metrics['map50']:.4f}")
        logger.info(f"⏱️  耗时: {training_duration:.2f} 小时")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"训练失败: {e}")
        logger.error(traceback.format_exc())
        latest_training_result = None

def find_latest_custom_model():
    """查找最新的自定义训练模型"""
    if not MODEL_DIR.exists():
        return None

    custom_models = []
    for f in MODEL_DIR.glob("*.pt"):
        name = f.stem
        if name not in ['best', 'last', 'yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x']:
            if name.startswith(('annotation', 'custom', 'best')):
                custom_models.append((f, f.stat().st_mtime))

    if not custom_models:
        return None

    custom_models.sort(key=lambda x: x[1], reverse=True)
    latest_model = custom_models[0][0]
    logger.info(f"找到最新模型: {latest_model.name}")
    return str(latest_model)


def generate_version_name():
    """生成有意义的版本名称"""
    if not MODEL_DIR.exists():
        return "annotation1"

    existing_numbers = []
    for f in MODEL_DIR.glob("*.pt"):
        name = f.stem
        if name.startswith('annotation'):
            try:
                num = int(name.replace('annotation', ''))
                existing_numbers.append(('annotation', num))
            except ValueError:
                pass
        elif name.startswith('best') and name != 'best':
            try:
                num = int(name.replace('best', ''))
                existing_numbers.append(('best', num))
            except ValueError:
                pass

    if not existing_numbers:
        return "annotation1"

    max_num = max(num for _, num in existing_numbers)
    next_num = max_num + 1

    if next_num % 3 == 0:
        return f"best{next_num}"
    else:
        return f"annotation{next_num}"


def save_training_info(version, model_path, results, base_model):
    """保存训练信息到 JSON 文件"""
    info = {
        "version": version,
        "model_path": str(model_path),
        "base_model": str(base_model),
        "trained_at": datetime.now().isoformat(),
        "metrics": {
            "map50": float(results.results_dict.get('metrics/mAP50(B)', 0)),
            "map75": float(results.results_dict.get('metrics/mAP75(B)', 0)),
            "map50_95": float(results.results_dict.get('metrics/mAP50-95(B)', 0)),
        },
        "training_config": {
            "epochs": results.epochs,
            "imgsz": results.args.imgsz,
            "batch": results.args.batch,
        }
    }

    info_file = MODEL_DIR / f"{version}.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ 训练信息已保存: {info_file}")


def prepare_yaml(dataset_dir: Path = None) -> str:
    """生成data.yaml"""
    base = (dataset_dir or DATASET_DIR).absolute()

    classes_file = base / "classes.txt"
    if classes_file.exists():
        with open(classes_file, 'r') as f:
            names = [l.strip() for l in f if l.strip()]
    else:
        labels_dir = base / "train" / "labels"
        class_ids = set()
        if labels_dir.exists():
            for f in labels_dir.glob("*.txt"):
                with open(f) as file:
                    for line in file:
                        parts = line.strip().split()
                        if parts:
                            class_ids.add(int(parts[0]))
        names = [f"class_{i}" for i in sorted(class_ids)] if class_ids else ["object"]

    yaml = f"""path: {base}
train: train/images
val: val/images
nc: {len(names)}
names: {names}
"""
    yaml_path = base / "data.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml)

    return str(yaml_path)




# ========== API 路由 ==========
# main.py - 在文件中找到合适的位置添加（建议在其他 API 路由附近）

@app.get("/api/projects/{project_id}/folder-tasks")
async def get_folder_tasks(
        project_id: str,
        status: str = Query(..., description="文件夹状态: pending/labeling/done"),
        db: Session = Depends(get_db)
):
    """获取指定文件夹（按状态）的任务列表"""
    logger.info(f"【FOLDER-TASKS】获取文件夹任务 | project_id={project_id}, status={status}")

    # 查询该项目的所有文件
    files_result = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.status == status
    ).all()

    if not files_result:
        return {"tasks": [], "total": 0}

    project_uuid = uuid.UUID(project_id)
    project_record = db.query(Project).filter(Project.id == project_uuid).first()
    lineage_context = _get_project_lineage_context(project_id)
    allow_cross_project_fallback = _can_access_cross_project_annotations(project_record, lineage_context)
    is_reviewer_workspace = bool(
        project_record and _is_reviewer_workspace_owner(project_record.owner_id, lineage_context)
    )
    prefer_reviewed_task = bool(
        project_record and _should_prefer_reviewed_task(project_record.owner_id, lineage_context)
    )
    # 已标注文件是否可见由 project_files.status 控制；这里不再做“仅 reviewed 可读”的全局限制，
    # 避免将轻微偏差（自动融合）任务错误挡在分享者视角之外。
    reviewed_only_for_owner = False

    file_ids = [str(f.id) for f in files_result]
    storage_paths = [f.storage_path for f in files_result if f.storage_path]

    # 优先按 file_id 命中任务（文件原拥有者/接收者自己的任务）
    tasks_result = supabase.table("tasks").select("*").in_("file_id", file_ids).execute()
    direct_tasks = tasks_result.data or []
    direct_task_map = {task.get("file_id"): task for task in direct_tasks if task.get("file_id")}

    # 兜底：按 storage_path 补齐跨分享副本的任务（分享者可查看接收者已标注结果）
    storage_tasks = []
    if allow_cross_project_fallback and storage_paths:
        storage_task_result = (
            supabase.table("tasks")
            .select("*")
            .in_("project_id", lineage_context.get("related_project_ids") or [project_id])
            .in_("image_storage_path", storage_paths)
            .order("updated_at", desc=True)
            .execute()
        )
        storage_tasks = storage_task_result.data or []

    storage_task_map: dict[str, list[dict[str, Any]]] = {}
    for task in storage_tasks:
        task_storage_path = task.get("image_storage_path")
        if task_storage_path:
            storage_task_map.setdefault(task_storage_path, []).append(task)

    # 按当前项目文件顺序构建任务列表，确保每张图都能映射到最合适任务
    matched_pairs = []
    for file_record in files_result:
        direct_task = direct_task_map.get(str(file_record.id))
        storage_task = _pick_preferred_storage_task(
            storage_task_map.get(file_record.storage_path, []),
            prefer_reviewed=prefer_reviewed_task,
            reviewed_only=reviewed_only_for_owner,
        )
        direct_task_status = str((direct_task or {}).get("status") or "").lower()
        direct_reviewed_task = direct_task if direct_task_status == "reviewed" else None
        if reviewed_only_for_owner:
            matched_task = storage_task or direct_reviewed_task
        else:
            matched_task = (
                storage_task or direct_task
                if prefer_reviewed_task
                else direct_task or storage_task
            )
        if matched_task:
            matched_pairs.append((file_record, matched_task, direct_task))

    # 按文件创建时间排序
    matched_pairs.sort(key=lambda pair: pair[0].created_at or datetime.min)

    # 构建响应
    task_list = []
    for file_record, task, direct_task in matched_pairs:
        used_fallback_task = bool(task and (not direct_task or task.get("id") != direct_task.get("id")))
        annotations = _load_task_annotations(task)
        task_obj = {
            "task_id": task["id"],
            "file_id": str(file_record.id),
            "filename": file_record.filename or task.get("filename", ""),
            "image_url": task.get("image_url"),
            "status": task.get("status", "labeling"),
            "project_name": task.get("project_name"),
            "project_id": project_id,
            "use_keywords": task.get("use_keywords", False),
            "keywords": task.get("keywords", []),
            "annotations": annotations
        }
        task_list.append(
            _apply_collaboration_preview(
                task_obj,
                task,
                prefer_integrated_annotations=(
                    is_reviewer_workspace and used_fallback_task and task.get("status") != "reviewed"
                ),
                include_collaboration_preview=is_reviewer_workspace,
            )
        )

    logger.info(f"【FOLDER-TASKS】返回 {len(task_list)} 个任务")
    return {"tasks": task_list, "total": len(task_list)}


@app.get("/api/projects/{project_id}/file-task")
async def get_file_task(
        project_id: str,
        file_id: str = Query(..., description="文件ID"),
        db: Session = Depends(get_db)
):
    """获取单个文件对应的标注任务"""
    logger.info(f"【FILE-TASK】获取文件任务 | project_id={project_id}, file_id={file_id}")

    project_uuid = uuid.UUID(project_id)
    project_record = db.query(Project).filter(Project.id == project_uuid).first()
    if not project_record:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证文件存在
    file_record = db.query(ProjectFile).filter(
        ProjectFile.id == file_id,
        ProjectFile.project_id == project_uuid
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 先按 file_id 查询任务
    task_result = supabase.table("tasks").select("*").eq("file_id", file_id).maybe_single().execute()
    task = task_result.data if task_result else None
    lineage_context = _get_project_lineage_context(project_id)
    used_fallback_task = False
    is_reviewer_workspace = _is_reviewer_workspace_owner(project_record.owner_id, lineage_context)
    prefer_reviewed_task = _should_prefer_reviewed_task(project_record.owner_id, lineage_context)
    reviewed_only_for_owner = False

    # 兜底：按 storage_path 查询同源任务（满足“谁标注谁可看，分享者均可看”）
    allow_cross_project_fallback = _can_access_cross_project_annotations(project_record, lineage_context)
    if file_record.storage_path and allow_cross_project_fallback:
        fallback_result = (
            supabase.table("tasks")
            .select("*")
            .in_("project_id", lineage_context.get("related_project_ids") or [project_id])
            .eq("image_storage_path", file_record.storage_path)
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )
        fallback_tasks = fallback_result.data if fallback_result else []
        fallback_task = _pick_preferred_storage_task(
            fallback_tasks or [],
            prefer_reviewed=prefer_reviewed_task,
            reviewed_only=reviewed_only_for_owner,
        )
        if reviewed_only_for_owner:
            direct_task = task
            direct_task_status = str((direct_task or {}).get("status") or "").lower()
            if fallback_task:
                task = fallback_task
                used_fallback_task = not direct_task or task.get("id") != direct_task.get("id")
            elif direct_task_status != "reviewed":
                task = None
        elif prefer_reviewed_task and fallback_task:
            direct_task = task
            task = fallback_task
            used_fallback_task = not direct_task or task.get("id") != direct_task.get("id")
        elif not task and fallback_task:
            task = fallback_task
            used_fallback_task = True

    if not task:
        return {"task": None}

    # 查询草稿或标注
    annotations = _load_task_annotations(task)

    task_obj = {
        "task_id": task["id"],
        "file_id": file_id,
        "filename": file_record.filename,
        "storage_path": file_record.storage_path,
        "image_url": task.get("image_url"),
        "status": task.get("status", "labeling"),
        "project_name": task.get("project_name", ""),
        "project_id": project_id,
        "use_keywords": task.get("use_keywords", False),
        "keywords": task.get("keywords", []),
        "annotations": annotations
    }

    return {
        "task": _apply_collaboration_preview(
            task_obj,
            task,
            prefer_integrated_annotations=(
                is_reviewer_workspace and used_fallback_task and task.get("status") != "reviewed"
            ),
            include_collaboration_preview=is_reviewer_workspace,
        )
    }


@app.get("/api/projects/{project_id}/tasks/{task_id}/adjacent")
async def get_adjacent_task(
        project_id: str,
        task_id: str,
        direction: str = Query(..., pattern="^(next|prev)$"),
        db: Session = Depends(get_db)
):
    """获取当前任务的下一个或上一个任务"""
    logger.info(f"【ADJACENT】获取相邻任务 | project_id={project_id}, task_id={task_id}, direction={direction}")

    # 获取当前任务
    current_task_result = supabase.table("tasks").select("*").eq("id", task_id).maybe_single().execute()
    if not current_task_result.data:
        raise HTTPException(status_code=404, detail="任务不存在")

    current_task = current_task_result.data
    current_file_id = current_task.get("file_id")

    # 获取同项目的所有任务，按创建时间排序
    all_tasks_result = supabase.table("tasks").select("*").eq("project_id", project_id).order("created_at").execute()
    all_tasks = all_tasks_result.data or []

    # 找到当前任务索引
    current_index = -1
    for i, t in enumerate(all_tasks):
        if t["id"] == task_id:
            current_index = i
            break

    if current_index == -1:
        raise HTTPException(status_code=404, detail="当前任务不在项目任务列表中")

    # 计算目标索引
    if direction == "next":
        target_index = current_index + 1
        if target_index >= len(all_tasks):
            return {"task": None, "message": "已经是最后一个任务"}
    else:
        target_index = current_index - 1
        if target_index < 0:
            return {"task": None, "message": "已经是第一个任务"}

    target_task = all_tasks[target_index]

    # 获取文件信息
    file_result = db.query(ProjectFile).filter(ProjectFile.id == target_task.get("file_id")).first()

    # 获取标注/草稿
    annotations = _load_task_annotations(target_task)

    task_obj = {
        "task_id": target_task["id"],
        "file_id": target_task.get("file_id"),
        "filename": file_result.filename if file_result else "",
        "storage_path": file_result.storage_path if file_result else "",
        "image_url": target_task.get("image_url"),
        "status": target_task.get("status", "labeling"),
        "project_name": target_task.get("project_name", ""),
        "project_id": project_id,
        "use_keywords": target_task.get("use_keywords", False),
        "keywords": target_task.get("keywords", []),
        "annotations": annotations
    }

    return {
        "task": task_obj,
        "current_index": target_index,
        "total": len(all_tasks),
        "direction": direction
    }


@app.get("/api/projects/{project_id}/all-labeling-tasks")
async def get_all_project_labeling_tasks(
        project_id: str,
        db: Session = Depends(get_db)
):
    """获取项目中所有标注中状态的任务（用于标注页面导航）"""
    logger.info(f"【ALL-LABELING】获取项目所有标注中任务 | project_id={project_id}")

    # 查询该项目所有标注中状态的文件
    files_result = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.status == 'labeling'
    ).order_by(ProjectFile.created_at).all()

    if not files_result:
        return {"tasks": [], "total": 0}

    file_ids = [str(f.id) for f in files_result]

    # 查询对应的任务
    tasks_result = supabase.table("tasks").select("*").in_("file_id", file_ids).execute()
    tasks = tasks_result.data or []

    # 按文件创建时间排序（保持文件夹内的顺序）
    file_order = {str(f.id): f.created_at for f in files_result}
    tasks.sort(key=lambda t: file_order.get(t.get("file_id", ""), datetime.min))

    # 构建响应
    task_list = []
    for task in tasks:
        # 获取文件信息
        file_id = task.get("file_id")
        file_info = next((f for f in files_result if str(f.id) == file_id), None)
        annotations = _load_task_annotations(task)

        task_list.append({
            "task_id": task["id"],
            "file_id": file_id,
            "filename": file_info.filename if file_info else task.get("filename", ""),
            "image_url": task.get("image_url"),
            "status": task.get("status", "labeling"),
            "project_name": task.get("project_name", ""),
            "project_id": project_id,
            "use_keywords": task.get("use_keywords", False),
            "keywords": task.get("keywords", []),
            "annotations": annotations
        })

    logger.info(f"【ALL-LABELING】返回 {len(task_list)} 个标注中任务")
    return {"tasks": task_list, "total": len(task_list)}
@app.get("/")
def index():
    return {"message": "后端启动成功", "service": "智能标注系统API"}


@app.post("/api/predict")
async def predict_image(
        file: UploadFile = File(...),
        keywords: Optional[str] = Form(None),
        confidence_threshold: float = Form(0.25)
):
    """通用图片预测端点（用于测试图片模式）"""
    try:
        # 解析关键词
        target_keywords = []
        if keywords:
            try:
                target_keywords = json.loads(keywords)
                if isinstance(target_keywords, list):
                    target_keywords = [k.strip().lower() for k in target_keywords]
            except:
                pass

        # 读取图片
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # 运行模型，使用传入的置信度阈值
        model, version = model_manager.get()
        results = model(image, conf=confidence_threshold, iou=0.45)

        # 解析结果
        raw_annotations = []
        img_width, img_height = image.size

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                label = model.names[int(box.cls[0])]

                # 关键词过滤
                if target_keywords and label.lower() not in target_keywords:
                    continue

                assigned_color = get_label_color(label)

                raw_annotations.append({
                    "id": f"ann_{uuid.uuid4().hex[:6]}",
                    "label": label,
                    "x": round(max(0, x1), 2),
                    "y": round(max(0, y1), 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 3),
                    "color": assigned_color
                })

        # 去重
        annotations = remove_duplicate_annotations(raw_annotations, iou_threshold=0.85)
        removed_count = len(raw_annotations) - len(annotations)

        # 生成任务ID并保存图片
        task_id = f"upload_{uuid.uuid4().hex[:12]}"

        # 保存上传的图片到本地
        filename = f"{task_id}.jpg"
        local_path = UPLOAD_DIR / filename
        with open(local_path, "wb") as f:
            f.write(image_data)

        # 构建图片URL
        image_url = f"{LOCAL_UPLOADS_BASE_URL}/local-uploads/{filename}"

        return {
            "success": True,
            "task_id": task_id,
            "image_url": image_url,
            "image_storage_path": str(local_path),
            "annotations": annotations,
            "model_version": version,
            "stats": {
                "raw_count": len(raw_annotations),
                "final_count": len(annotations),
                "removed_duplicates": removed_count
            },
            "message": f"检测到 {len(annotations)} 个目标{'（已去重）' if removed_count > 0 else ''}"
        }

    except Exception as e:
        logger.error(f"通用预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================= 新增：预标注生成与任务分发 =================
from fastapi.concurrency import run_in_threadpool


@app.post("/api/projects/{project_id}/sessions", response_model=AnnotationSessionResponse)
async def create_annotation_session(
        project_id: str,
        payload: AnnotationSessionCreate,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db)
):
    """创建标注会话，生成项目名_序号格式的任务ID，防止重复创建
    对于已有标注的文件，直接返回已有标注，不再进行AI预测"""
    target_keywords = [k.strip().lower() for k in payload.keywords] if payload.keywords else []
    confidence_threshold = getattr(payload, 'confidence_threshold', 0.25)  # 默认置信度阈值 0.25
    bucket = supabase.storage.from_("project-files")
    current_user = _get_current_user_if_available(db, authorization)

    logger.info(f"【SESSION-001】开始创建标注会话 | project_id={project_id}, file_ids={payload.file_ids}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.error(f"【SESSION-002】项目不存在 | project_id={project_id}")
        raise HTTPException(status_code=404, detail="项目不存在")

    project_name = project.name
    logger.info(f"【SESSION-003】找到项目 | project_name={project_name}")

    tasks = []
    updated_file_ids = []

    for idx, file_id in enumerate(payload.file_ids):
        logger.info(f"【SESSION-004】处理文件 | idx={idx}, file_id={file_id}")

        project_file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
        if not project_file:
            logger.warning(f"【SESSION-005】文件不存在 | file_id={file_id}")
            continue

        initial_status = project_file.status
        logger.info(f"【SESSION-006】文件初始状态 | file_id={file_id}, status={initial_status}")

        # 检查该文件是否已有任务
        existing_task = supabase.table("tasks").select("id,status").eq("file_id", str(file_id)).execute()

        if existing_task.data and len(existing_task.data) > 0:
            existing_task_id = existing_task.data[0]["id"]
            existing_status = existing_task.data[0].get("status", "annotating")
            logger.info(
                f"【SESSION-008】文件已有任务 | file_id={file_id}, task_id={existing_task_id}, task_status={existing_status}")

            # 更新文件状态为 labeling（如果需要）
            if project_file.status != "labeling":
                logger.info(
                    f"【SESSION-009】需要更新文件状态 | file_id={file_id}, from={project_file.status} to=labeling")
                project_file.status = "labeling"
                updated_file_ids.append(str(file_id))
                logger.info(f"【SESSION-010】内存中状态已修改 | file_id={file_id}, current_status={project_file.status}")
            else:
                logger.info(f"【SESSION-011】文件状态已是labeling | file_id={file_id}")

            # 获取已有任务信息和标注（关键修改：直接返回已有标注，不再AI预测）
            task_info = supabase.table("tasks").select("*").eq("id", existing_task_id).execute()
            if task_info.data:
                task_data = task_info.data[0]
                task_status = task_data.get("status", "labeling")

                if task_status == "completed":
                    logger.info(f"【SESSION-012】任务状态为completed，重置为labeling | task_id={existing_task_id}")
                    supabase.table("tasks").update({
                        "status": "labeling",
                        "completed_at": None,
                        "annotations_count": 0
                    }).eq("id", existing_task_id).execute()
                    task_status = "labeling"
                    logger.info(f"【SESSION-013】任务状态已重置 | task_id={existing_task_id}")

                # 查询已有标注（草稿或已提交）
                existing_annotations = []
                if task_status == "completed":
                    anns_result = supabase.table("annotations").select("*").eq("task_id", existing_task_id).execute()
                    if anns_result.data:
                        existing_annotations = anns_result.data
                        logger.info(f"【SESSION-014a】加载已完成标注 {len(existing_annotations)} 个")
                else:
                    draft_result = supabase.table("drafts").select("*").eq("task_id", existing_task_id).maybe_single().execute()
                    if draft_result and draft_result.data:
                        existing_annotations = draft_result.data.get("annotations_json", [])
                        logger.info(f"【SESSION-014b】加载草稿标注 {len(existing_annotations)} 个")

                # ✅ 关键修改：已有标注的文件，直接返回已有标注，不再进行AI预测
                task_obj = AnnotationSessionTask(
                    task_id=task_data["id"],
                    file_id=str(file_id),
                    filename=project_file.filename,
                    storage_path=project_file.storage_path,
                    image_url=task_data["image_url"],
                    project_id=project_id,
                    project_name=task_data.get("project_name", project_name),
                    use_keywords=payload.use_keywords,
                    keywords=payload.keywords or [],
                    status=task_status,
                    annotations=existing_annotations  # 返回已有标注
                )
                tasks.append(task_obj)
                bind_task_to_user(db, task_id=task_data["id"], user=current_user, task_row=task_data)
                record_task_started(
                    db,
                    task_id=task_data["id"],
                    user=current_user,
                    task_row=task_data,
                )
                logger.info(f"【SESSION-014】已有任务添加到返回列表 | task_id={task_data['id']}, 标注数={len(existing_annotations)}")
            continue

        # 新文件处理（待标注文件夹过来的）- 进行AI预测
        logger.info(f"【SESSION-015】新文件，创建新任务并进行AI预测 | file_id={file_id}")

        if project_file.status != "labeling":
            logger.info(f"【SESSION-016】更新新文件状态 | file_id={file_id}, from={project_file.status} to=labeling")
            project_file.status = "labeling"
            updated_file_ids.append(str(file_id))
        else:
            logger.info(f"【SESSION-017】新文件状态已是labeling | file_id={file_id}")

        # 生成任务ID
        existing_tasks_result = supabase.table("tasks").select("id").ilike("id", f"{project_name}_%").execute()
        existing_count = len(existing_tasks_result.data) if existing_tasks_result.data else 0
        task_number = existing_count + 1
        task_id = f"{project_name}_{task_number:03d}"
        logger.info(f"【SESSION-018】生成任务ID | task_id={task_id}")

        image_url = bucket.get_public_url(project_file.storage_path)
        logger.info(f"【SESSION-019】图片URL | task_id={task_id}")

        # 运行AI预测（只有新文件才进行）
        annotations = []
        try:
            logger.info(f"【SESSION-020】开始AI预测 | task_id={task_id}")
            file_bytes = bucket.download(project_file.storage_path)
            result = await run_prediction(
                image_data=file_bytes,
                keywords=target_keywords if payload.use_keywords else None,
                save_draft=False,
                task_id=None,
                confidence_threshold=confidence_threshold
            )
            annotations = result["annotations"]
            logger.info(f"【SESSION-021】AI预测完成 | task_id={task_id}, annotations_count={len(annotations)}")
        except Exception as e:
            logger.error(f"【SESSION-022】AI预测失败 | task_id={task_id}, error={str(e)}")

        # 创建任务记录
        try:
            task_insert_data = {
                "id": task_id,
                "image_url": image_url,
                "image_storage_path": project_file.storage_path,
                "status": "labeling",
                "project_name": project_name,
                "project_id": project_id,
                "file_id": str(file_id),
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
                "annotations_count": 0
            }
            logger.info(f"【SESSION-023】插入任务到Supabase | task_id={task_id}")
            supabase.table("tasks").upsert(task_insert_data).execute()
            bind_task_to_user(db, task_id=task_id, user=current_user, task_row=task_insert_data)
            record_task_started(
                db,
                task_id=task_id,
                user=current_user,
                task_row=task_insert_data,
            )
            logger.info(f"【SESSION-024】任务创建成功 | task_id={task_id}")
        except Exception as e:
            logger.error(f"【SESSION-025】创建任务失败 | task_id={task_id}, error={str(e)}")
            continue

        # 保存预标注草稿
        if annotations:
            try:
                logger.info(f"【SESSION-026】保存预标注草稿 | task_id={task_id}, annotations_count={len(annotations)}")
                supabase.table("drafts").upsert({
                    "task_id": task_id,
                    "annotations_json": annotations,
                    "user_id": current_user.id if current_user else "system",
                    "saved_at": datetime.now().isoformat()
                }).execute()
                logger.info(f"【SESSION-027】草稿保存成功 | task_id={task_id}")
            except Exception as e:
                logger.warning(f"【SESSION-028】保存草稿失败 | task_id={task_id}, error={str(e)}")

        task_obj = AnnotationSessionTask(
            task_id=task_id,
            file_id=str(file_id),
            filename=project_file.filename,
            storage_path=project_file.storage_path,
            image_url=image_url,
            project_id=project_id,
            project_name=project_name,
            use_keywords=payload.use_keywords,
            keywords=payload.keywords or [],
            status="labeling",
            annotations=annotations
        )
        tasks.append(task_obj)
        logger.info(f"【SESSION-029】新任务添加到返回列表 | task_id={task_id}")

    # 统一提交文件状态更新
    logger.info(f"【SESSION-030】准备提交数据库事务 | updated_file_ids={updated_file_ids}")

    if updated_file_ids:
        try:
            for fid in updated_file_ids:
                f = db.query(ProjectFile).filter(ProjectFile.id == fid).first()
                logger.info(f"【SESSION-031】提交前内存状态确认 | file_id={fid}, status={f.status if f else 'None'}")

            logger.info(f"【SESSION-032】执行db.commit()...")
            db.commit()
            logger.info(f"【SESSION-033】db.commit() 成功")

            # 使用新会话验证数据库状态
            logger.info(f"【SESSION-034】验证数据库实际状态...")
            from app.db.session import SessionLocal
            verify_session = SessionLocal()
            try:
                for fid in updated_file_ids:
                    f = verify_session.query(ProjectFile).filter(ProjectFile.id == fid).first()
                    db_status = f.status if f else 'NOT_FOUND'
                    logger.info(f"【SESSION-035】数据库实际状态 | file_id={fid}, status={db_status}")
            finally:
                verify_session.close()
                logger.info(f"【SESSION-036】验证会话已关闭")

        except Exception as e:
            db.rollback()
            logger.error(f"【SESSION-037】提交失败，已回滚 | error={str(e)}")
            raise HTTPException(status_code=500, detail=f"更新文件状态失败: {e}")
    else:
        logger.info(f"【SESSION-038】没有需要更新的文件状态")

    # 构建响应
    response = AnnotationSessionResponse(
        success=True,
        project_id=project_id,
        project_name=project_name,
        use_keywords=payload.use_keywords,
        keywords=payload.keywords or [],
        tasks=tasks,
        first_task=tasks[0] if tasks else None
    )
    logger.info(f"【SESSION-039】标注会话创建完成 | tasks_count={len(tasks)}")

    return response


# 云端模型切换接口示例
@app.post("/api/models/switch-cloud")
async def switch_cloud_model(request: ModelSwitchRequest):
    # 从 Supabase 获取模型信息
    model = supabase.table('model_versions') \
        .select('*') \
        .eq('version_name', request.name) \
        .single() \
        .execute()

    # 下载模型文件（如果需要）
    # 或直接使用云端模型路径
    return {"success": True, "model": model.data}
@app.post("/api/tasks/{task_id}/smart-annotate")
async def smart_annotate_incremental(
        task_id: str,
        payload: dict,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
):
    """
    增量式智能预标注：检测新物体，只添加不与已有标注重叠的框
    """
    try:
        logger.info(f"【SMART-ANNOTATE】开始增量预标注 | task_id={task_id}")
        current_user = _get_current_user_if_available(db, authorization)

        # 获取任务信息
        task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task_res.data:
            raise HTTPException(404, detail="任务不存在")

        task = task_res.data[0]
        bind_task_to_user(db, task_id=task_id, user=current_user, task_row=task)
        image_url = task.get("image_url")
        image_storage_path = task.get("image_storage_path")

        # 获取已有标注（从草稿或已完成标注）
        existing_annotations = []
        draft_result = supabase.table("drafts").select("*").eq("task_id", task_id).maybe_single().execute()
        if draft_result and draft_result.data:
            existing_annotations = draft_result.data.get("annotations_json", [])
            logger.info(f"【SMART-ANNOTATE】从草稿加载已有标注 {len(existing_annotations)} 个")

        if not existing_annotations and task.get("status") == "completed":
            anns_result = supabase.table("annotations").select("*").eq("task_id", task_id).execute()
            if anns_result.data:
                existing_annotations = anns_result.data
                logger.info(f"【SMART-ANNOTATE】从已完成标注加载 {len(existing_annotations)} 个")

        # 获取关键词过滤
        keywords = payload.get("keywords", [])
        target_keywords = [k.strip().lower() for k in keywords] if keywords else []
        iou_threshold = payload.get("iou_threshold", 0.5)  # 默认IOU阈值0.5

        # 加载图片
        bucket = supabase.storage.from_("project-files")
        try:
            file_bytes = bucket.download(image_storage_path)
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception as e:
            logger.error(f"【SMART-ANNOTATE】加载图片失败: {e}")
            raise HTTPException(500, detail=f"加载图片失败: {str(e)}")

        # 运行AI预测
        model, version = model_manager.get()
        results = model(image, conf=0.25, iou=0.45)

        # 解析AI检测结果
        raw_ai_annotations = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                label = model.names[int(box.cls[0])]

                # 关键词过滤
                if target_keywords and label.lower() not in target_keywords:
                    continue

                assigned_color = get_label_color(label)

                raw_ai_annotations.append({
                    "id": f"ann_{uuid.uuid4().hex[:6]}",
                    "label": label,
                    "x": round(max(0, x1), 2),
                    "y": round(max(0, y1), 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 3),
                    "color": assigned_color,
                    "source": "ai",  # 标记为AI生成
                    "is_new": True  # 标记为新检测
                })

        # AI结果内部去重
        unique_ai_annotations = remove_duplicate_annotations(raw_ai_annotations, iou_threshold=0.85)
        logger.info(f"【SMART-ANNOTATE】AI检测到 {len(unique_ai_annotations)} 个唯一目标")

        # 与已有标注进行IOU去重
        new_annotations = []
        skipped_count = 0

        for ai_ann in unique_ai_annotations:
            is_duplicate = False

            for exist_ann in existing_annotations:
                # 计算IOU
                iou = calculate_iou(ai_ann, {
                    'x': exist_ann.get('x', 0),
                    'y': exist_ann.get('y', 0),
                    'width': exist_ann.get('width', 0),
                    'height': exist_ann.get('height', 0)
                })

                # 如果IOU超过阈值，认为是同一物体，跳过
                if iou > iou_threshold:
                    is_duplicate = True
                    skipped_count += 1
                    logger.debug(f"跳过重复标注: {ai_ann['label']} IOU={iou:.2f}")
                    break

            if not is_duplicate:
                new_annotations.append(ai_ann)

        logger.info(
            f"【SMART-ANNOTATE】去重完成: 原始{len(unique_ai_annotations)}个, 跳过{skipped_count}个, 新增{len(new_annotations)}个")

        # 合并新旧标注
        all_annotations = existing_annotations + new_annotations

        # 保存到草稿
        if new_annotations:
            try:
                supabase.table("drafts").upsert({
                    "task_id": task_id,
                    "annotations_json": all_annotations,
                    "user_id": current_user.id if current_user else "system",
                    "saved_at": datetime.now().isoformat()
                }).execute()
                record_task_progress(
                    db,
                    task_id=task_id,
                    user=current_user,
                    task_row=task,
                    save_count_increment=1,
                    payload_snapshot={"source": "smart_annotate", "new_annotations": len(new_annotations)},
                )
                logger.info(f"【SMART-ANNOTATE】合并标注已保存到草稿 | 总计{len(all_annotations)}个")
            except Exception as e:
                logger.warning(f"【SMART-ANNOTATE】保存草稿失败: {e}")

        return {
            "success": True,
            "annotations": new_annotations,  # 只返回新增的
            "all_annotations": all_annotations,  # 全部标注
            "model_version": version,
            "stats": {
                "existing_count": len(existing_annotations),
                "ai_detected": len(unique_ai_annotations),
                "duplicate_skipped": skipped_count,
                "new_added": len(new_annotations),
                "total_now": len(all_annotations)
            },
            "message": f"检测到 {len(unique_ai_annotations)} 个目标，{skipped_count} 个与已有标注重复，新增 {len(new_annotations)} 个"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"【SMART-ANNOTATE】增量预标注失败: {e}")
        raise HTTPException(500, detail=f"智能预标注失败: {str(e)}")
@app.post("/api/project/{project_id}/move-to-done")
async def move_to_done(
        project_id: str,
        payload: dict,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db)
):
    """前端点击「提交标注」后触发：将数据库中的文件状态更为已标注"""
    task_id = payload.get("taskId")

    # 验证任务存在
    task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(404, detail=f"任务 {task_id} 不存在")

    task_data = task_res.data[0]
    current_user = _get_current_user_if_available(db, authorization)
    bind_task_to_user(db, task_id=task_id, user=current_user, task_row=task_data)
    storage_path = task_data.get("image_storage_path")

    updated_rows = 0
    notify_usernames: set[str] = set()
    integration_result = _collaborative_auto_integrate(task_data)
    # 仅同步到当前标注者项目与分享者项目（谁标注谁可看，分享者均可看）
    if storage_path:
        project_uuid = uuid.UUID(project_id)
        current_project = db.query(Project).filter(Project.id == project_uuid).first()
        related_projects = [current_project] if current_project else []
        root_project_id = project_uuid
        root_project = current_project
        reviewer_project_ids: set[uuid.UUID] = set()

        if current_project:
            root_project_id = current_project.source_project_id or current_project.id
            related_projects = (
                db.query(Project)
                .filter((Project.id == root_project_id) | (Project.source_project_id == root_project_id))
                .all()
            )
            root_project = next(
                (project for project in related_projects if project.id == root_project_id),
                current_project,
            )

            notify_usernames = {current_project.owner_id}
            if root_project and root_project.owner_id:
                notify_usernames.add(root_project.owner_id)

            if current_project.reviewer_id:
                reviewer_user = db.query(User).filter(User.id == current_project.reviewer_id).first()
                if reviewer_user:
                    notify_usernames.add(reviewer_user.username)
                    reviewer_projects = [
                        project
                        for project in related_projects
                        if project.owner_id == reviewer_user.username
                    ]
                    if not reviewer_projects and root_project:
                        reviewer_project = Project(
                            name=f"[审核] {root_project.name} - {reviewer_user.username}",
                            description=root_project.description,
                            owner_id=reviewer_user.username,
                            source_project_id=root_project_id,
                            is_shared_copy=True,
                            shared_by=current_project.shared_by or root_project.owner_id,
                            shared_at=datetime.utcnow(),
                            share_message=current_project.share_message,
                            organization_nickname=current_project.organization_nickname,
                            share_accepted_at=None,
                            share_mode=current_project.share_mode,
                            reviewer_id=current_project.reviewer_id,
                        )
                        db.add(reviewer_project)
                        db.flush()

                        source_files = (
                            db.query(ProjectFile)
                            .filter(ProjectFile.project_id == root_project_id)
                            .all()
                        )
                        for source_file in source_files:
                            db.add(
                                ProjectFile(
                                    project_id=reviewer_project.id,
                                    filename=source_file.filename,
                                    storage_path=source_file.storage_path,
                                    mime_type=source_file.mime_type,
                                    size_bytes=source_file.size_bytes,
                                    uploaded_by=current_project.shared_by or current_project.owner_id,
                                    status="archived",
                                )
                            )
                        related_projects.append(reviewer_project)
                        reviewer_projects = [reviewer_project]

                    reviewer_project_ids = {project.id for project in reviewer_projects}

        related_project_ids = [project.id for project in related_projects if project]
        reviewer_should_receive = bool(
            integration_result.get("ready")
            and integration_result.get("review_triggered")
        )
        # 协作审核流程中，分享者（root）在审核完成前不进入“已标注”。
        visible_done_project_ids = {project_uuid}
        if not reviewer_should_receive:
            visible_done_project_ids.add(root_project_id)

        matched_files = []
        if related_project_ids:
            matched_files = (
                db.query(ProjectFile)
                .filter(
                    ProjectFile.storage_path == storage_path,
                    ProjectFile.project_id.in_(related_project_ids),
                )
                .all()
            )

        for project_file in matched_files:
            target_status = None
            if project_file.project_id in visible_done_project_ids:
                target_status = "done"
            elif project_file.project_id in reviewer_project_ids:
                target_status = "done" if reviewer_should_receive else "archived"

            if target_status and project_file.status != target_status:
                project_file.status = target_status
                updated_rows += 1

        if updated_rows:
            db.commit()
            logger.info(f"文件状态已同步 | storage_path={storage_path}, updated={updated_rows}")
            await progress_ws_manager.emit_to_users(
                list(notify_usernames),
                {
                    "type": "PROJECT_PROGRESS_UPDATED",
                    "owner": current_project.owner_id if current_project else None,
                    "project_id": str(root_project_id) if current_project else project_id,
                    "task_id": task_id,
                    "storage_path": storage_path,
                    "updated_rows": updated_rows,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        elif not matched_files:
            logger.warning(f"未找到对应的文件记录: {storage_path}")

    # ✅ 修复：更新任务状态为 completed
    supabase.table("tasks").update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "annotations_count": task_data.get("annotations_count", 0)
    }).eq("id", task_id).execute()

    logger.info(f"任务 {task_id} 已完成")

    return {"success": True, "message": "任务已完成", "task_id": task_id}


@app.post("/api/projects/{project_id}/review/confirm")
async def confirm_review_result(
        project_id: str,
        payload: dict,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db)
):
    """审核员确认裁决结果：归档到“已审核”，并同步分享者查看最终结果。"""
    try:
        user = _require_current_user(db, authorization)

        try:
            project_uuid = uuid.UUID(str(project_id))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="项目 ID 无效")

        current_project = db.query(Project).filter(Project.id == project_uuid).first()
        if not current_project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if current_project.owner_id != user.username:
            raise HTTPException(status_code=403, detail="仅当前审核项目拥有者可以提交审核结果")

        lineage_context = _get_project_lineage_context(project_id)
        reviewer_username = lineage_context.get("reviewer_username")
        if not reviewer_username or reviewer_username != user.username:
            raise HTTPException(status_code=403, detail="仅项目审核人可以确认裁决结果")

        file_id = payload.get("file_id")
        if not file_id:
            raise HTTPException(status_code=400, detail="缺少 file_id")

        try:
            file_uuid = uuid.UUID(str(file_id))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="文件 ID 无效")

        annotations = payload.get("annotations")
        if not isinstance(annotations, list):
            raise HTTPException(status_code=400, detail="annotations 必须为数组")

        file_record = db.query(ProjectFile).filter(
            ProjectFile.id == file_uuid,
            ProjectFile.project_id == project_uuid,
        ).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="审核文件不存在")

        source_task = None
        source_task_id = payload.get("task_id")
        if source_task_id:
            source_task_result = (
                supabase.table("tasks").select("*").eq("id", source_task_id).limit(1).execute()
            )
            source_tasks = source_task_result.data or []
            source_task = source_tasks[0] if source_tasks else None

        if not source_task:
            fallback_result = (
                supabase.table("tasks")
                .select("*")
                .in_("project_id", lineage_context.get("related_project_ids") or [project_id])
                .eq("image_storage_path", file_record.storage_path)
                .order("updated_at", desc=True)
                .limit(10)
                .execute()
            )
            fallback_tasks = fallback_result.data or []
            source_task = _pick_preferred_storage_task(fallback_tasks, prefer_reviewed=False)

        if not source_task:
            raise HTTPException(status_code=404, detail="未找到待审核任务")

        base_source = payload.get("base_source")
        metric_task_id = payload.get("metric_task_id")
        metric_source_task = source_task

        if metric_task_id:
            metric_task_result = (
                supabase.table("tasks").select("*").eq("id", metric_task_id).limit(1).execute()
            )
            metric_task_rows = metric_task_result.data or []
            metric_task = metric_task_rows[0] if metric_task_rows else None
            if _is_metric_task_eligible(
                    metric_task,
                    file_storage_path=file_record.storage_path,
                    lineage_context=lineage_context,
            ):
                metric_source_task = metric_task
            else:
                logger.warning(
                    "审核记分任务校验失败，回退到默认任务 | metric_task_id=%s | source_task_id=%s",
                    metric_task_id,
                    source_task.get("id"),
                )
        else:
            metric_source_task = _resolve_metric_source_task_from_base_source(
                fallback_task=source_task,
                base_source=base_source,
                lineage_context=lineage_context,
                file_storage_path=file_record.storage_path,
                db=db,
            )

        metric_task_effective_id = metric_source_task.get("id")
        if not metric_task_effective_id:
            metric_source_task = source_task
            metric_task_effective_id = metric_source_task.get("id")
        if not metric_task_effective_id:
            raise HTTPException(status_code=500, detail="审核记分任务无效")

        source_annotations = _load_task_annotations(metric_source_task)

        review_task_result = (
            supabase.table("tasks")
            .select("*")
            .eq("project_id", project_id)
            .eq("file_id", str(file_record.id))
            .order("updated_at", desc=True)
            .limit(5)
            .execute()
        )
        review_tasks = review_task_result.data or []
        review_task = review_tasks[0] if review_tasks else None
        review_task_id = (
            review_task.get("id")
            if review_task
            else f"review_{str(project_uuid).replace('-', '')[:8]}_{str(file_record.id).replace('-', '')[:8]}"
        )

        now_iso = datetime.now().isoformat()
        task_payload = {
            "id": review_task_id,
            "image_url": source_task.get("image_url"),
            "image_storage_path": file_record.storage_path,
            "status": "reviewed",
            "project_name": current_project.name,
            "project_id": project_id,
            "file_id": str(file_record.id),
            "created_at": review_task.get("created_at") if review_task else now_iso,
            "completed_at": now_iso,
            "annotations_count": len(annotations),
        }
        supabase.table("tasks").upsert(task_payload).execute()
        supabase.table("drafts").delete().eq("task_id", review_task_id).execute()
        supabase.table("annotations").delete().eq("task_id", review_task_id).execute()

        annotation_rows = []
        for ann in annotations:
            annotation_rows.append({
                "id": f"review_ann_{uuid.uuid4().hex[:12]}",
                "task_id": review_task_id,
                "label": ann.get("label", "未命名"),
                "x": ann.get("x", 0),
                "y": ann.get("y", 0),
                "width": ann.get("width", 0),
                "height": ann.get("height", 0),
                "confidence": ann.get("confidence", 1.0),
                "color": ann.get("color", DEFAULT_COLOR),
                "annotated_by": user.username,
                "created_at": now_iso,
            })
        if annotation_rows:
            _insert_annotations_rows(annotation_rows)

        root_project_id = current_project.source_project_id or current_project.id
        related_projects = (
            db.query(Project)
            .filter((Project.id == root_project_id) | (Project.source_project_id == root_project_id))
            .all()
        )
        related_project_ids = [project.id for project in related_projects]
        matched_files = []
        if related_project_ids:
            matched_files = (
                db.query(ProjectFile)
                .filter(
                    ProjectFile.storage_path == file_record.storage_path,
                    ProjectFile.project_id.in_(related_project_ids),
                )
                .all()
            )

        updated_rows = 0
        for project_file in matched_files:
            target_status = project_file.status
            if project_file.project_id == current_project.id:
                # project_files.status 在数据库约束中不接受 reviewed，审核确认后统一落到 done
                target_status = "done"
            elif project_file.project_id == root_project_id:
                target_status = "done"

            if target_status != project_file.status:
                project_file.status = target_status
                updated_rows += 1

        db.commit()

        notify_usernames = {
            username
            for username in {
                user.username,
                lineage_context.get("root_owner"),
                current_project.shared_by,
            }
            if username
        }
        await progress_ws_manager.emit_to_users(
            list(notify_usernames),
            {
                "type": "PROJECT_PROGRESS_UPDATED",
                "owner": current_project.owner_id,
                "project_id": str(root_project_id),
                "file_id": str(file_record.id),
                "storage_path": file_record.storage_path,
                "updated_rows": updated_rows,
                "timestamp": now_iso,
            },
        )
        collaboration_snapshot = (
            source_task.get("collaboration_integration")
            if isinstance(source_task.get("collaboration_integration"), dict)
            else None
        )
        record_review_result(
            db,
            task_id=metric_task_effective_id,
            reviewer=user,
            reviewed_annotations=annotations,
            submitted_annotations=source_annotations,
            reviewed_at=datetime.now(),
            integration_result=collaboration_snapshot,
        )

        return {
            "success": True,
            "message": "审核结果已确认",
            "task_id": review_task_id,
            "file_id": str(file_record.id),
            "reviewed_count": len(annotation_rows),
            "metric_task_id": metric_task_effective_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("确认裁决并归档失败 | project_id=%s | payload_keys=%s", project_id, list(payload.keys()))
        raise HTTPException(status_code=500, detail=f"确认裁决失败: {str(exc)}")


# =================================================================
# ========== 公共预测函数 ==========
async def run_prediction(
        image_data: bytes,
        keywords: Optional[List[str]] = None,
        save_draft: bool = False,
        task_id: Optional[str] = None,
        confidence_threshold: float = 0.25
) -> Dict[str, Any]:
    """
    运行AI预测，返回标注结果
    被 /api/predict 和 /api/projects/{project_id}/sessions 共用
    """
    try:
        # 加载图片
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # 运行模型，使用传入的置信度阈值
        model, version = model_manager.get()
        results = model(image, conf=confidence_threshold, iou=0.45)

        # 关键词过滤
        target_keywords = [k.strip().lower() for k in keywords] if keywords else []

        # 解析结果
        raw_annotations = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                label = model.names[int(box.cls[0])]

                # 关键词过滤
                if target_keywords and label.lower() not in target_keywords:
                    continue

                assigned_color = get_label_color(label)

                raw_annotations.append({
                    "id": f"ann_{uuid.uuid4().hex[:6]}",
                    "label": label,
                    "x": round(max(0, x1), 2),
                    "y": round(max(0, y1), 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 3),
                    "color": assigned_color
                })

        # 去重
        annotations = remove_duplicate_annotations(raw_annotations, iou_threshold=0.85)
        removed_count = len(raw_annotations) - len(annotations)

        # 保存草稿（可选）
        if save_draft and task_id and annotations:
            try:
                supabase.table("drafts").upsert({
                    "task_id": task_id,
                    "annotations_json": annotations,
                    "user_id": "system_ai",
                    "saved_at": datetime.now().isoformat()
                }).execute()
                logger.info(f"预标注草稿已保存: {task_id}, {len(annotations)} 个框")
            except Exception as e:
                logger.warning(f"保存草稿失败: {e}")

        return {
            "success": True,
            "annotations": annotations,
            "model_version": version,
            "stats": {
                "raw_count": len(raw_annotations),
                "final_count": len(annotations),
                "removed_duplicates": removed_count
            },
            "message": f"检测到 {len(annotations)} 个目标{'（已去重）' if removed_count > 0 else ''}"
        }

    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise

    async def run_prediction_with_dedup(
            image_data: bytes,
            existing_annotations: List[Dict[str, Any]] = None,
            keywords: Optional[List[str]] = None,
            iou_threshold: float = 0.5,
            save_draft: bool = False,
            task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        运行AI预测，并与已有标注进行去重，只返回新检测到的物体
        """
        try:
            existing_annotations = existing_annotations or []

            # 加载图片
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_width, img_height = image.size

            # 运行模型，使用传入的置信度阈值
            model, version = model_manager.get()
            results = model(image, conf=confidence_threshold, iou=0.45)

            # 关键词过滤
            target_keywords = [k.strip().lower() for k in keywords] if keywords else []

            # 解析AI检测结果
            raw_annotations = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    label = model.names[int(box.cls[0])]

                    # 关键词过滤
                    if target_keywords and label.lower() not in target_keywords:
                        continue

                    assigned_color = get_label_color(label)

                    raw_annotations.append({
                        "id": f"ann_{uuid.uuid4().hex[:6]}",
                        "label": label,
                        "x": round(max(0, x1), 2),
                        "y": round(max(0, y1), 2),
                        "width": round(x2 - x1, 2),
                        "height": round(y2 - y1, 2),
                        "confidence": round(float(box.conf[0]), 3),
                        "color": assigned_color,
                        "source": "ai"  # 标记来源
                    })

            # 第一步：AI结果内部去重（NMS）
            unique_ai_annotations = remove_duplicate_annotations(raw_annotations, iou_threshold=0.85)

            # 第二步：与已有标注去重
            new_annotations = []
            skipped_count = 0

            for ai_ann in unique_ai_annotations:
                is_duplicate = False

                for exist_ann in existing_annotations:
                    # 计算IOU
                    iou = calculate_iou(ai_ann, {
                        'x': exist_ann.get('x', 0),
                        'y': exist_ann.get('y', 0),
                        'width': exist_ann.get('width', 0),
                        'height': exist_ann.get('height', 0)
                    })

                    # 如果IOU超过阈值，认为是同一物体
                    if iou > iou_threshold:
                        is_duplicate = True
                        skipped_count += 1
                        logger.debug(f"跳过重复标注: {ai_ann['label']} IOU={iou:.2f}")
                        break

                if not is_duplicate:
                    new_annotations.append(ai_ann)

            # 保存草稿（可选）
            if save_draft and task_id and new_annotations:
                try:
                    # 合并新旧标注
                    all_annotations = existing_annotations + new_annotations
                    supabase.table("drafts").upsert({
                        "task_id": task_id,
                        "annotations_json": all_annotations,
                        "user_id": "system_ai",
                        "saved_at": datetime.now().isoformat()
                    }).execute()
                    logger.info(f"合并标注草稿已保存: {task_id}, 共 {len(all_annotations)} 个框")
                except Exception as e:
                    logger.warning(f"保存草稿失败: {e}")

            return {
                "success": True,
                "annotations": new_annotations,  # 只返回新标注
                "all_annotations": existing_annotations + new_annotations,  # 全部标注
                "model_version": version,
                "stats": {
                    "raw_count": len(raw_annotations),
                    "ai_unique_count": len(unique_ai_annotations),
                    "existing_count": len(existing_annotations),
                    "duplicate_skipped": skipped_count,
                    "final_new_count": len(new_annotations)
                },
                "message": f"检测到 {len(unique_ai_annotations)} 个目标，{skipped_count} 个与已有标注重复，新增 {len(new_annotations)} 个"
            }

        except Exception as e:
            logger.error(f"智能预测去重失败: {e}")
            raise

@app.post("/api/tasks/batch")
async def batch_create_tasks(tasks: List[dict]):
    """主系统批量推送任务"""
    results = []

    for task_info in tasks:
        task_id = task_info.get("task_id")
        image_url = task_info.get("image_url")
        project_name = task_info.get("project_name")

        try:
            import urllib.request
            with urllib.request.urlopen(image_url, timeout=30) as response:
                image_data = response.read()

            file_name = f"uploads/{task_id}.jpg"
            local_path = UPLOAD_DIR / f"{task_id}.jpg"
            with open(local_path, "wb") as f:
                f.write(image_data)

            try:
                supabase.storage.from_("images").upload(
                    path=file_name,
                    file=image_data,
                    file_options={"content-type": "image/jpeg"}
                )
                storage_url = supabase.storage.from_("images").get_public_url(file_name)
            except:
                storage_url = build_local_upload_url(f"{task_id}.jpg")
            task_data = {
                "id": task_id,
                "image_url": storage_url,
                "image_storage_path": file_name,
                "status": "pending",
                "project_name": project_name,
                "source_url": image_url,
                "created_at": datetime.now().isoformat()
            }
            supabase.table("tasks").upsert(task_data).execute()

            results.append({
                "task_id": task_id,
                "success": True,
                "status": "created"
            })

        except Exception as e:
            results.append({
                "task_id": task_id,
                "success": False,
                "error": str(e)
            })

    return {
        "success": True,
        "processed": len(results),
        "results": results
    }


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, payload: dict):
    """标注完成，通知主系统"""
    try:
        annotations = payload.get("annotations", [])

        supabase.table("tasks").update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "annotations_count": len(annotations)
        }).eq("id", task_id).execute()

        for ann in annotations:
            ann_data = {
                "id": ann.get("id", f"ann_{uuid.uuid4().hex[:8]}"),
                "task_id": task_id,
                "label": ann.get("label"),
                "x": ann.get("x"),
                "y": ann.get("y"),
                "width": ann.get("width"),
                "height": ann.get("height"),
                "confidence": ann.get("confidence", 1.0),
                "annotated_by": ann.get("annotated_by", "human"),
                "created_at": datetime.now().isoformat()
            }
            _insert_annotations_rows([ann_data])

        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已完成"
        }

    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    logger.info(f"查询任务: {task_id}")

    try:
        result = supabase.table("tasks").select("*").eq("id", task_id).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        task = result.data[0]

        # ✅ 确保 project_name 正确
        if not task.get("project_name") and "_" in task_id:
            task["project_name"] = task_id.rsplit("_", 1)[0]
            logger.info(f"推断项目名: {task['project_name']}")

        logger.info(f"返回任务: {task_id}, 项目: {task.get('project_name')}")

        # 查询草稿
        draft = None
        try:
            draft_result = supabase.table("drafts").select("*").eq("task_id", task_id).maybe_single().execute()
            draft = draft_result.data if draft_result else None
        except Exception as e:
            logger.warning(f"查询草稿失败: {e}")

        if draft and draft.get("annotations_json"):
            draft_annotations = [_normalize_annotation_box(ann) for ann in draft["annotations_json"]]
            return {
                "task": task,
                "annotations": draft_annotations,
                "source": "draft"
            }

        # 查询已提交标注
        anns_result = supabase.table("annotations").select("*").eq("task_id", task_id).execute()
        anns = [_normalize_annotation_box(ann) for ann in (anns_result.data or [])]

        return {
            "task": task,
            "annotations": anns,
            "source": "database"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@app.post("/api/tasks/{task_id}/predict")
async def predict_existing_task(task_id: str, payload: dict):
    """对已存在的任务进行智能标注，支持关键词过滤"""
    keywords = payload.get("keywords", [])
    target_keywords = [k.strip().lower() for k in keywords] if keywords else []

    task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(404, detail="任务不存在")

    task = task_res.data[0]
    image_url = task.get("image_url")
    image_storage_path = task.get("image_storage_path")

    try:
        if image_storage_path and os.path.exists(image_storage_path):
            image = Image.open(image_storage_path).convert("RGB")
        else:
            req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                image_data = response.read()
            image = Image.open(io.BytesIO(image_data)).convert("RGB")

        model, version = model_manager.get()
        results = model(image, conf=0.25, iou=0.45)

        raw_annotations = []
        for r in results:
            for box in r.boxes:
                label = model.names[int(box.cls[0])]

                if target_keywords and label.lower() not in target_keywords:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                assigned_color = get_label_color(label)

                raw_annotations.append({
                    "id": f"ann_{uuid.uuid4().hex[:6]}",
                    "label": label,
                    "x": round(max(0, x1), 2),
                    "y": round(max(0, y1), 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 3),
                    "color": assigned_color
                })

        annotations = remove_duplicate_annotations(raw_annotations, iou_threshold=0.85)

        return {
            "success": True,
            "annotations": annotations,
            "model_version": version,
            "message": f"成功识别 {len(annotations)} 个目标"
        }
    except Exception as e:
        logger.error(f"预测现有任务失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/training/status")
async def training_status():
    """获取训练状态和模型列表"""
    try:
        is_valid, msg, details = DatasetValidator.validate()

        local_models = []
        if MODEL_DIR.exists():
            for f in MODEL_DIR.glob("*.pt"):
                model_name = f.stem
                is_active = (model_name == model_manager.active_version)

                local_models.append({
                    "name": model_name,
                    "path": str(f),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "is_active": is_active
                })
            local_models.sort(key=lambda x: x["modified"], reverse=True)

        cloud_models = []
        try:
            cloud_result = supabase.table("model_versions").select("*").order("created_at", desc=True).limit(
                10).execute()
            if cloud_result.data:
                for m in cloud_result.data:
                    is_active = (m.get("version_name") == model_manager.active_version)
                    cloud_models.append({
                        **m,
                        "is_active": is_active
                    })
        except Exception as e:
            logger.warning(f"获取云端模型失败: {e}")

        global latest_training_result
        pending_upload = False
        latest_model_data = None

        if latest_training_result is not None:
            if not latest_training_result.get("uploaded", False) and not latest_training_result.get("skipped", False):
                pending_upload = True
                latest_model_data = latest_training_result

        return {
            "dataset_ready": is_valid,
            "dataset_message": msg,
            "dataset_stats": details.get("stats", {}),
            "current_model": model_manager.active_version,
            "local_models": local_models,
            "cloud_models": cloud_models,
            "pending_upload": pending_upload,
            "latest_model": latest_model_data if pending_upload else None,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }
    except Exception as e:
        logger.error(f"获取训练状态失败: {e}")
        return {
            "dataset_ready": False,
            "dataset_message": f"检查失败: {str(e)}",
            "dataset_stats": {},
            "current_model": "",
            "local_models": [],
            "cloud_models": [],
            "pending_upload": False,
            "latest_model": None,
            "cuda_available": False
        }


@app.post("/api/training/start")
async def start_training(
        background_tasks: BackgroundTasks,
        dataset_id: str = Query(default=None, description="指定数据集ID，不指定则使用活动数据集"),
        epochs: int = Query(default=50, ge=1, le=500, description="训练轮数"),
        batch: int = Query(default=16, ge=1, le=128, description="批次大小"),
        model_size: str = Query(default='n', regex='^[nsmlx]$', description="模型大小: n/s/m/l/x"),
        use_aug: bool = Query(default=True, description="是否使用数据增强"),
        optimizer: str = Query(default='AdamW', description="优化器"),
        lr0: float = Query(default=0.001, ge=0.0001, le=0.1, description="初始学习率"),
        imgsz: int = Query(default=640, ge=320, le=1280, description="输入图片尺寸"),
        patience: int = Query(default=20, ge=5, le=100, description="早停耐心值"),
        weight_decay: float = Query(default=0.0005, ge=0.0, le=0.01, description="权重衰减"),
        dropout: float = Query(default=0.0, ge=0.0, le=0.5, description="Dropout比率"),
        label_smoothing: float = Query(default=0.0, ge=0.0, le=0.1, description="标签平滑"),
        freeze: int = Query(default=0, ge=0, le=24, description="冻结层数"),
        warmup_epochs: int = Query(default=3, ge=0, le=10, description="预热轮数"),
        mosaic: float = Query(default=1.0, ge=0.0, le=1.0, description="Mosaic增强概率"),
        mixup: float = Query(default=0.1, ge=0.0, le=1.0, description="MixUp增强概率"),
        copy_paste: float = Query(default=0.0, ge=0.0, le=1.0, description="CopyPaste增强概率"),
        degrees: float = Query(default=15.0, ge=0.0, le=90.0, description="旋转角度"),
        scale: float = Query(default=0.5, ge=0.0, le=1.0, description="缩放比例"),
        shear: float = Query(default=5.0, ge=0.0, le=20.0, description="剪切角度"),
):
    """启动训练"""
    try:
        target_dataset_id = dataset_id or dataset_manager.active_dataset_id or "default"

        # 处理基础数据集：从 Storage 下载到本地
        if target_dataset_id == "default":
            cache_path = await _download_base_dataset_to_cache()
            if not cache_path:
                raise HTTPException(400, detail="基础数据集下载失败")

            # 验证下载的数据集
            is_valid, msg, details = DatasetValidator.validate(cache_path)
            if not is_valid:
                raise HTTPException(400, detail=f"数据集未准备好: {msg}")

            train_count = details["stats"]["train"]
            # ... 继续训练逻辑

        else:
            # 原有逻辑...
            if not dataset_manager.is_cached(target_dataset_id):
                path = dataset_manager.get_dataset_path(target_dataset_id)
                if not path:
                    raise HTTPException(400, detail=f"数据集 {target_dataset_id} 不存在")
            cache_path = dataset_manager.get_cache_path(target_dataset_id)
            # ... 原有验证和训练逻辑

        # 启动训练任务
        background_tasks.add_task(
            run_training,
            project_id=target_dataset_id,
            dataset_id=target_dataset_id,
            epochs=epochs,
            batch=batch,
            model_size=model_size,
            use_aug=use_aug,
            optimizer=optimizer,
            lr0=lr0,
            imgsz=imgsz,
            patience=patience,
            weight_decay=weight_decay,
            dropout=dropout,
            label_smoothing=label_smoothing,
            freeze=freeze,
            warmup_epochs=warmup_epochs,
            mosaic=mosaic,
            mixup=mixup,
            copy_paste=copy_paste,
            degrees=degrees,
            scale=scale,
            shear=shear,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


async def _download_base_dataset_to_cache() -> Path | None:
    """将基础数据集从 Storage 下载到本地缓存"""
    cache_dir = Path("./cache/datasets/default")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已缓存
    if (cache_dir / "data.yaml").exists():
        train_dir = cache_dir / "train" / "images"
        if train_dir.exists() and len(list(train_dir.glob("*"))) > 0:
            logger.info("基础数据集已缓存")
            return cache_dir

    try:
        supabase_client = get_supabase_client()
        bucket = "datasets"

        # 下载 classes.txt, data.yaml
        for filename in ["classes.txt", "data.yaml"]:
            try:
                data = supabase_client.storage.from_(bucket).download(filename)
                if data:
                    with open(cache_dir / filename, "wb") as f:
                        f.write(data if isinstance(data, bytes) else data.encode())
            except Exception as e:
                logger.warning(f"下载 {filename} 失败: {e}")

        # 下载 train/images 和 train/labels
        await _download_folder_from_storage(supabase_client, bucket, "train/images", cache_dir / "train" / "images")
        await _download_folder_from_storage(supabase_client, bucket, "train/labels", cache_dir / "train" / "labels")

        # 下载 val/images 和 val/labels
        await _download_folder_from_storage(supabase_client, bucket, "val/images", cache_dir / "val" / "images")
        await _download_folder_from_storage(supabase_client, bucket, "val/labels", cache_dir / "val" / "labels")

        # 生成 data.yaml（如果没有）
        if not (cache_dir / "data.yaml").exists():
            classes_file = cache_dir / "classes.txt"
            if classes_file.exists():
                with open(classes_file) as f:
                    names = [l.strip() for l in f if l.strip()]
            else:
                names = ["object"]

            yaml_content = f"""path: {cache_dir.absolute()}
train: train/images
val: val/images
nc: {len(names)}
names: {names}
"""
            with open(cache_dir / "data.yaml", "w") as f:
                f.write(yaml_content)

        logger.info(f"基础数据集下载完成: {cache_dir}")
        return cache_dir

    except Exception as e:
        logger.error(f"下载基础数据集失败: {e}")
        return None


async def _download_folder_from_storage(client, bucket: str, remote_path: str, local_path: Path):
    """从 Storage 下载整个文件夹"""
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        files = client.storage.from_(bucket).list(remote_path)
        if not files:
            return

        for file_info in files:
            filename = file_info.get('name')
            if not filename:
                continue

            remote_file_path = f"{remote_path}/{filename}"
            local_file_path = local_path / filename

            try:
                data = client.storage.from_(bucket).download(remote_file_path)
                if data:
                    with open(local_file_path, "wb") as f:
                        f.write(data if isinstance(data, bytes) else data.encode())
            except Exception as e:
                logger.warning(f"下载文件 {remote_file_path} 失败: {e}")

    except Exception as e:
        logger.warning(f"列出文件夹 {remote_path} 失败: {e}")

@app.post("/api/models/upload")
async def upload_model_to_cloud():
    """手动上传最新模型到云端"""
    global latest_training_result

    try:
        if not latest_training_result:
            raise HTTPException(400, detail="没有待上传的模型")

        if latest_training_result.get("uploaded"):
            raise HTTPException(400, detail="模型已经上传过了")

        local_path = latest_training_result["local_path"]
        version = latest_training_result["version_name"]
        db_id = latest_training_result.get("id")

        if not os.path.exists(local_path):
            raise HTTPException(404, detail="本地模型文件不存在")

        logger.info(f"☁️  开始上传模型到云端: {version}")
        try:
            with open(local_path, "rb") as f:
                upload_path = f"weights/{version}.pt"
                supabase.storage.from_("models").upload(upload_path, f)

            cloud_path = f"models/weights/{version}.pt"
            logger.info(f"✅ 云端上传成功: {cloud_path}")

            if db_id:
                supabase.table("model_versions").update({
                    "model_path": cloud_path
                }).eq("id", db_id).execute()

            latest_training_result["uploaded"] = True
            latest_training_result["cloud_path"] = cloud_path

            return {
                "success": True,
                "message": "模型已上传到云端",
                "version": version,
                "cloud_path": cloud_path
            }

        except Exception as upload_err:
            logger.error(f"云端上传失败: {upload_err}")
            raise HTTPException(500, detail=f"上传失败: {str(upload_err)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/models/skip-upload")
async def skip_cloud_upload():
    """跳过云端上传"""
    global latest_training_result

    try:
        if not latest_training_result:
            raise HTTPException(400, detail="没有待上传的模型")

        latest_training_result["uploaded"] = True
        latest_training_result["skipped"] = True

        return {
            "success": True,
            "message": "已跳过云端上传",
            "version": latest_training_result["version_name"]
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/models/switch")
async def switch_model(payload: dict):
    """切换模型"""
    try:
        path = payload.get("path")
        name = payload.get("name")

        logger.info(f"尝试切换模型: name={name}, path={path}")

        if not path or not os.path.exists(path):
            raise HTTPException(400, detail=f"模型文件不存在: {path}")

        model_manager.switch(path, name)
        logger.info(f"模型加载成功: {name}")

        try:
            supabase.table("model_versions").update({"is_active": False}).neq("id", 0).execute()
            supabase.table("model_versions").update({"is_active": True}).eq("version_name", name).execute()
        except Exception as db_err:
            logger.error(f"数据库更新失败: {db_err}")

        return {"success": True, "message": f"已切换至: {name}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换模型失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail=f"切换失败: {str(e)}")


@app.post("/api/annotations/{task_id}")
async def save_annotations(
        task_id: str,
        payload: dict,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db)
):
    """保存标注，支持 项目名_序号 格式"""
    try:
        anns = payload.get("annotations", [])
        is_draft = payload.get("is_draft", True)
        current_user = _get_current_user_if_available(db, authorization)
        if not current_user and payload.get("user_id"):
            current_user = db.query(User).filter(User.id == str(payload.get("user_id"))).first()
        user_id = current_user.id if current_user else payload.get("user_id", "anonymous")
        tracker_payload = parse_tracker_payload(payload)

        logger.info(f"保存标注: task_id={task_id}, is_draft={is_draft}, count={len(anns)}")

        # 验证任务存在
        task_check = (
            supabase
            .table("tasks")
            .select("id,project_name,project_id,image_storage_path")
            .eq("id", task_id)
            .execute()
        )
        if not task_check.data:
            raise HTTPException(404, detail=f"任务不存在: {task_id}")

        task_row = task_check.data[0]
        project_name = task_row.get("project_name", "unknown")
        bind_task_to_user(db, task_id=task_id, user=current_user, task_row=task_row)

        if is_draft:
            # 保存草稿
            supabase.table("drafts").upsert({
                "task_id": task_id,
                "annotations_json": anns,
                "user_id": user_id,
                "saved_at": datetime.now().isoformat()
            }).execute()
            record_task_progress(
                db,
                task_id=task_id,
                user=current_user,
                task_row=task_row,
                started_at=tracker_payload.get("started_at"),
                last_saved_at=tracker_payload.get("last_activity_at"),
                work_seconds=tracker_payload.get("work_seconds"),
                save_count_total=tracker_payload.get("save_count"),
                payload_snapshot={
                    "annotation_count": len(anns),
                    "mode": "draft",
                },
            )
            return {"success": True, "status": "draft_saved", "count": len(anns)}
        else:
            # 提交最终标注
            supabase.table("drafts").delete().eq("task_id", task_id).execute()
            # 保证幂等：重复提交时清理旧结果
            supabase.table("annotations").delete().eq("task_id", task_id).execute()

            # 保存标注到 annotations 表 - 使用批量插入
            if anns:
                annotations_data = []
                for ann in anns:
                    annotations_data.append({
                        "id": ann.get("id", f"ann_{uuid.uuid4().hex[:8]}"),
                        "task_id": task_id,
                        "label": ann.get("label"),
                        "x": ann.get("x"),
                        "y": ann.get("y"),
                        "width": ann.get("width"),
                        "height": ann.get("height"),
                        "confidence": ann.get("confidence", 1.0),
                        "color": ann.get("color", "#ff0000"),
                        "annotated_by": user_id,
                        "created_at": datetime.now().isoformat()
                    })

                # 批量插入
                _insert_annotations_rows(annotations_data)

            # 更新任务状态为已完成
            supabase.table("tasks").update({
                "status": "completed",
                "annotations_count": len(anns),
                "completed_at": datetime.now().isoformat()
            }).eq("id", task_id).execute()

            # 协作标注自动整合流程（不新增字段，仅返回整合与审核结果）
            integration_result = _collaborative_auto_integrate(task_row)
            record_task_submission(
                db,
                task_id=task_id,
                user=current_user,
                task_row=task_row,
                submitted_annotations=anns,
                started_at=tracker_payload.get("started_at"),
                submitted_at=tracker_payload.get("last_activity_at"),
                work_seconds=tracker_payload.get("work_seconds"),
                save_count=tracker_payload.get("save_count"),
                integration_result=integration_result,
                payload_snapshot={
                    "annotation_count": len(anns),
                    "mode": "submit",
                    "has_collaboration_review": bool(integration_result.get("review_triggered")),
                },
            )
            if integration_result.get("auto_integrated") and integration_result.get("fused_annotations"):
                final_task_id = (integration_result.get("source_task_ids") or [task_id])[0]
                _delete_auto_fusion_annotations(final_task_id)
                auto_rows = []
                for ann in integration_result["fused_annotations"]:
                    auto_rows.append({
                        "id": ann.get("id", f"auto_{uuid.uuid4().hex[:8]}"),
                        "task_id": final_task_id,
                        "label": ann.get("label"),
                        "x": ann.get("x"),
                        "y": ann.get("y"),
                        "width": ann.get("width"),
                        "height": ann.get("height"),
                        "confidence": ann.get("confidence", 1.0),
                        "color": ann.get("color", DEFAULT_COLOR),
                        "annotated_by": "auto_fusion",
                        "created_at": datetime.now().isoformat()
                    })
                if auto_rows:
                    _insert_annotations_rows(auto_rows)
                    integration_result["final_result_saved_to_task_id"] = final_task_id

            return {
                "success": True,
                "status": "submitted",
                "count": len(anns),
                "project_name": project_name,
                "task_id": task_id,
                "collaboration_integration": integration_result
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labels")
async def get_labels():
    default_labels = [
        {"id": 1, "name": "person", "color": "#ff0000", "category": "human"},
        {"id": 2, "name": "car", "color": "#0000ff", "category": "vehicle"},
        {"id": 3, "name": "dog", "color": "#00ff00", "category": "animal"},
        {"id": 4, "name": "cat", "color": "#ffa500", "category": "animal"},
        {"id": 5, "name": "bird", "color": "#ffff00", "category": "animal"}
    ]

    try:
        if supabase is None:
            return {"labels": default_labels, "source": "default", "warning": "Supabase 未连接，使用默认标签"}

        res = supabase.table("label_configs").select("*").order("name").execute()

        if not res.data or len(res.data) == 0:
            return {"labels": default_labels, "source": "default", "warning": "数据库无标签，使用默认标签"}

        processed_labels = []
        for idx, item in enumerate(res.data):
            label_name = item.get("name") or item.get("label_name") or f"label_{idx}"
            label_color = item.get("color") or item.get("label_color") or "#1890ff"
            label_id = item.get("id") or idx
            processed_labels.append({
                "id": label_id,
                "name": label_name,
                "color": label_color,
                "category": item.get("category")
            })

        return {"labels": processed_labels, "source": "database", "count": len(processed_labels)}

    except Exception as e:
        return {"labels": default_labels, "source": "default", "error": str(e),
                "warning": f"查询失败({str(e)})，使用默认标签"}


@app.post("/api/labels")
async def create_label(payload: dict):
    try:
        data = {
            "name": payload["name"],
            "color": payload.get("color", "#1890ff"),
            "category": payload.get("category")
        }
        res = supabase.table("label_configs").insert(data).execute()
        return {"success": True, "label": res.data[0]}
    except Exception as e:
        if "duplicate" in str(e).lower():
            raise HTTPException(409, detail="标签已存在")
        raise HTTPException(500, detail=str(e))


@app.put("/api/labels/{name}")
async def update_label(name: str, payload: dict):
    try:
        res = supabase.table("label_configs").update({
            "color": payload.get("color", "#1890ff"),
            "category": payload.get("category")
        }).eq("name", name).execute()
        if res.data:
            return {"success": True, "label": res.data[0]}
        raise HTTPException(404, detail="标签不存在")
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.delete("/api/labels/{name}")
async def delete_label(name: str):
    try:
        supabase.table("label_configs").delete().eq("name", name).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/local-uploads/{filename}", name="get_local_upload")
async def get_local_upload(filename: str, request: Request):
    from urllib.parse import unquote
    decoded_filename = unquote(filename)
    path = UPLOAD_DIR / decoded_filename

    if path.exists():
        file_stat = path.stat()
        import mimetypes
        content_type, _ = mimetypes.guess_type(str(path))
        response = FileResponse(
            path,
            media_type=content_type or "image/jpeg",
            filename=decoded_filename
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["ETag"] = str(file_stat.st_mtime)
        return response

    raise HTTPException(status_code=404, detail=f"文件不存在: {decoded_filename}")


@app.post("/api/models/{model_name}/upload")
async def upload_specific_model(model_name: str):
    try:
        from urllib.parse import unquote
        model_name = unquote(model_name)
        model_path = MODEL_DIR / f"{model_name}.pt"
        if not model_path.exists():
            matching = list(MODEL_DIR.glob(f"*{model_name}*.pt"))
            if matching:
                model_path = matching[0]
            else:
                raise HTTPException(404, detail=f"未找到模型文件: {model_name}")

        file_size = model_path.stat().st_size
        upload_path = f"weights/{model_path.name}"
        cloud_path = f"models/{upload_path}"

        with open(model_path, "rb") as f:
            try:
                supabase.storage.from_("models").remove([upload_path])
            except Exception:
                pass
            supabase.storage.from_("models").upload(upload_path, f)

        try:
            existing = supabase.table("model_versions").select("*").eq("version_name", model_path.stem).execute()
            if existing.data:
                supabase.table("model_versions").update({
                    "model_path": cloud_path,
                    "local_path": str(model_path.absolute()),
                    "updated_at": datetime.now().isoformat()
                }).eq("version_name", model_path.stem).execute()
            else:
                supabase.table("model_versions").insert({
                    "version_name": model_path.stem,
                    "model_size": "unknown",
                    "model_path": cloud_path,
                    "local_path": str(model_path.absolute()),
                    "is_active": False,
                    "training_status": "completed",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).execute()
        except Exception as db_err:
            logger.warning(f"数据库更新失败（不影响上传）: {db_err}")

        return {
            "success": True,
            "message": "模型已上传到云端",
            "version": model_path.stem,
            "cloud_path": cloud_path,
            "size_mb": round(file_size / (1024 * 1024), 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail=f"上传失败: {str(e)}")


# ========== 数据集管理 API ==========


def _count_storage_images_exact(
        supabase_client: Any,
        bucket: str,
        folder_path: str,
        page_size: int = 100,
) -> int:
    total_count = 0
    offset = 0
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif'}

    while True:
        items = supabase_client.storage.from_(bucket).list(
            folder_path,
            {
                "limit": page_size,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if not items:
            break

        for item in items:
            name = str(item.get("name", "")).lower()
            if any(name.endswith(ext) for ext in image_extensions):
                total_count += 1

        if len(items) < page_size:
            break
        offset += page_size

    return total_count


def _read_storage_classes(supabase_client: Any, bucket: str, path: str) -> list[str]:

    try:
        file_response = supabase_client.storage.from_(bucket).download(path)
        if not file_response:
            return []
        content = file_response.decode("utf-8") if isinstance(file_response, bytes) else file_response
        return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as exc:
        logger.warning(f"read storage classes failed | path={path} | err={exc}")
        return []


async def _get_storage_dataset_status(
        dataset_id: str,
        storage_prefix: str,
        dataset_name: str,
) -> dict[str, Any]:
    """
    从 Supabase Storage 获取数据集状态。
    已加 Redis 缓存，避免每次打开训练页面都重复 list Storage 文件。
    """
    bucket = "datasets"
    normalized_prefix = storage_prefix.strip("/")

    cache_key = f"dataset:storage-status:{dataset_id}:{normalized_prefix or 'root'}"
    cached = _cache_get_json(cache_key)
    if cached:
        cached["is_active"] = dataset_manager.active_dataset_id == dataset_id
        cached["cache_hit"] = True
        return cached

    supabase_client = get_supabase_client()

    train_count = _count_storage_images_exact(
        supabase_client,
        bucket,
        f"{normalized_prefix}/train/images"
    )
    val_count = _count_storage_images_exact(
        supabase_client,
        bucket,
        f"{normalized_prefix}/val/images"
    )
    classes = _read_storage_classes(
        supabase_client,
        bucket,
        f"{normalized_prefix}/classes.txt"
    )

    total = train_count + val_count

    result = {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "exists": total > 0,
        "cached": False,
        "cache_path": f"storage://{bucket}/{normalized_prefix}",
        "stats": {
            "train": train_count,
            "val": val_count,
            "total": total,
            "classes": len(classes),
            "class_names": classes,
            "train_has_more": False,
            "val_has_more": False,
            "max_counted": total,
        },
        "is_active": dataset_manager.active_dataset_id == dataset_id,
        "storage_mode": True,
        "cache_hit": False,
    }

    # 数据集文件数量不需要秒级实时，缓存 5 分钟
    _cache_set_json(cache_key, result, ttl=300)

    return result


def _load_cloud_zip_datasets() -> list[dict[str, Any]]:
    try:
        response = (
            supabase.table("datasets")
            .select("*")
            .eq("status", "ready")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"load cloud zip datasets failed: {exc}")
        return []

    datasets: list[dict[str, Any]] = []
    for row in response.data or []:
        storage_path = str(row.get("storage_path") or "")
        if not storage_path.endswith(".zip"):
            continue

        dataset_id = str(row.get("dataset_id") or "")
        if not dataset_id:
            continue

        cache_path = dataset_cache_manager.get_cache_path(dataset_id)
        cached = dataset_cache_manager.is_cached(dataset_id)
        stats = row.get("stats") or {}
        datasets.append({
            "dataset_id": dataset_id,
            "id": dataset_id,
            "name": row.get("name") or dataset_id,
            "storage_prefix": "",
            "storage_path": storage_path,
            "bucket": row.get("bucket") or "datasets",
            "is_local": cached,
            "local_path": str(cache_path) if cached else None,
            "stats": stats,
            "is_zip_dataset": True,
            "is_active": dataset_manager.active_dataset_id == dataset_id,
        })

    return datasets


@app.get("/api/datasets")
async def list_datasets(
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    cache_key = _make_cache_key(
        "dataset:list",
        limit,
        offset,
        search or "",
        dataset_manager.active_dataset_id or "default"
    )

    cached = _cache_get_json(cache_key)
    if cached:
        cached["cache_hit"] = True
        return cached


    """
    获取数据集列表，支持分页和搜索
    解决基础数据集文件过多导致前端展示不下的问题
    """
    datasets = []

    # 1. 从 dataset_manager 获取
    manager_datasets = dataset_manager.list_available_datasets()
    datasets.extend(manager_datasets)
    datasets.extend(_load_cloud_zip_datasets())

    # 2. 添加基础数据集（从 Storage 检查）- 限制只检查结构，不列出所有文件
    try:
        bucket = "datasets"

        # 检查基础数据集是否存在（只检查关键目录，不遍历所有文件）
        train_exists = False
        try:
            # 只检查 train/images 目录是否存在，不列出所有文件
            train_list = supabase.storage.from_(bucket).list("train")
            train_exists = any(f.get('name') == 'images' for f in train_list)
        except Exception as e:
            logger.debug(f"检查 train 目录失败: {e}")
            pass

        if train_exists:
            # 只获取统计信息，不获取完整文件列表
            base_status = await _get_base_dataset_status_from_storage()
            datasets.insert(0, {
                "dataset_id": "default",
                "name": "基础数据集",
                "path": f"storage://{bucket}/",
                "stats": base_status["stats"],
                "cached": True,
                "is_active": dataset_manager.active_dataset_id == "default" or dataset_manager.active_dataset_id is None,
                "is_base": True  # 标记为基础数据集
            })
    except Exception as e:
        logger.warning(f"添加基础数据集到列表失败: {e}")

    # 3. 搜索过滤
    deduped_datasets: dict[str, dict[str, Any]] = {}
    for dataset in datasets:
        dataset_key = str(dataset.get("dataset_id") or dataset.get("id") or "")
        if dataset_key:
            deduped_datasets[dataset_key] = dataset
    datasets = list(deduped_datasets.values())

    for dataset in datasets:
        dataset_key = str(dataset.get("dataset_id") or dataset.get("id") or "")
        if dataset_key == "base":
            try:
                base_status = await _get_base_dataset_status_from_storage()
                dataset["stats"] = base_status["stats"]
                dataset["is_active"] = dataset_manager.active_dataset_id == "base"
            except Exception as exc:
                logger.warning(f"refresh base dataset stats failed: {exc}")

    if search:
        search_lower = search.lower()
        datasets = [
            d for d in datasets
            if search_lower in d.get("name", "").lower()
            or search_lower in d.get("dataset_id", "").lower()
        ]

    # 4. 分页
    total = len(datasets)
    paginated_datasets = datasets[offset:offset + limit]

    result = {
        "datasets": paginated_datasets,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "active_dataset_id": dataset_manager.active_dataset_id or "default",
        "cache_hit": False,
    }

    _cache_set_json(cache_key, result, ttl=60)

    return result


@app.post("/api/datasets/{dataset_id}/switch")
async def switch_dataset(dataset_id: str):
    """切换训练数据集"""
    try:
        # 处理前端传来的 undefined 或空值
        if not dataset_id or dataset_id.lower() in ("undefined", "null", "none", ""):
            dataset_id = "default"
            logger.info(f"数据集ID为 undefined，自动回退到 default")

        # 如果是 default，确保基础数据集可用
        if dataset_id == "default":
            # 检查基础数据集是否存在
            try:
                train_list = supabase.storage.from_("datasets").list("train")
                train_exists = any(f.get('name') == 'images' for f in train_list)
                if not train_exists:
                    raise HTTPException(400, detail="基础数据集不存在，请检查 Storage 中的 datasets bucket")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"检查基础数据集失败: {e}")

        success = dataset_manager.switch_dataset(dataset_id)
        if not success:
            try:
                db_dataset_result = supabase.table("datasets").select("*").eq("dataset_id",
                                                                              dataset_id).maybe_single().execute()
                db_dataset = db_dataset_result.data if db_dataset_result else None
            except Exception as db_lookup_err:
                logger.warning(f"lookup cloud dataset failed | dataset_id={dataset_id} | err={db_lookup_err}")
                db_dataset = None

            if db_dataset and str(db_dataset.get("storage_path") or "").endswith(".zip"):
                if not dataset_cache_manager.is_cached(dataset_id):
                    # 关键修复：捕获 download_with_progress 的具体异常
                    try:
                        await dataset_cache_manager.download_with_progress(
                            dataset_id=dataset_id,
                            storage_path=db_dataset.get("storage_path"),
                            bucket=db_dataset.get("bucket") or "datasets",
                        )
                    except Exception as download_err:
                        logger.error(f"数据集下载失败: {download_err}")
                        # 返回具体的下载错误，而不是 500 Internal Server Error
                        raise HTTPException(
                            status_code=400,
                            detail=f"数据集下载失败: {str(download_err)}"
                        )

                    cache_path = dataset_cache_manager.get_cache_path(dataset_id)
                    if cache_path.exists():
                        info = DatasetInfo(
                            id=dataset_id,
                            name=db_dataset.get("name") or dataset_id,
                            storage_prefix="",
                            is_local=True,
                        )
                        info.local_path = cache_path
                        info.stats = db_dataset.get("stats") or {}
                        dataset_manager.datasets[dataset_id] = info
                        dataset_manager.active_dataset_id = dataset_id
                        _cache_delete_pattern("dataset:list:*")
                        return {
                            "success": True,
                            "dataset_id": dataset_id,
                            "dataset_name": info.name,
                            "local_path": str(cache_path),
                            "stats": info.stats,
                            "message": f"已切换到数据集: {dataset_id}"
                        }

            # 如果切换失败且是 default，尝试初始化
            if dataset_id == "default":
                logger.info("尝试初始化默认数据集...")
                try:
                    base_status = await _get_base_dataset_status_from_storage()
                    if base_status.get("stats", {}).get("total", 0) > 0:
                        # 数据集存在，强制设置 active
                        dataset_manager.active_dataset_id = "default"
                        return {
                            "success": True,
                            "dataset_id": "default",
                            "dataset_name": "基础数据集",
                            "local_path": None,
                            "stats": base_status["stats"],
                            "message": "已切换到基础数据集（Storage 模式）"
                        }
                except Exception as init_err:
                    logger.error(f"初始化默认数据集失败: {init_err}")

            raise HTTPException(400, detail=f"无法切换到数据集: {dataset_id}，可能不存在或未准备好")

        path = dataset_manager.get_active_dataset_path()
        info = dataset_manager.datasets.get(dataset_id)
        _cache_delete_pattern("dataset:list:*")
        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset_name": info.name if info else dataset_id,
            "local_path": str(path) if path else None,
            "stats": info.stats if info else {},
            "message": f"已切换到数据集: {dataset_id}"
        }

    except HTTPException:
        raise  # FastAPI 会自动处理为 JSON 响应
    except Exception as e:
        logger.error(f"切换数据集异常: {e}")
        logger.error(traceback.format_exc())
        # 关键修复：所有未捕获的异常都转换为 HTTPException，确保返回 JSON 而不是 HTML
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/datasets/active")
async def get_active_dataset():
    """获取当前活动数据集信息"""
    # 如果 active_dataset_id 是 default 或 None 或 undefined，返回基础数据集信息
    active_id = dataset_manager.active_dataset_id
    if active_id in (None, "default", "undefined", "", "null"):
        try:
            base_status = await _get_base_dataset_status_from_storage()
            if base_status["stats"]["total"] > 0:
                return {
                    "active": True,
                    "dataset_id": "default",
                    "dataset_name": "基础数据集",
                    "local_path": None,
                    "storage_path": "storage://datasets/",
                    "config": {
                        "path": ".",
                        "train": "train/images",
                        "val": "val/images",
                        "nc": base_status["stats"]["classes"],
                        "names": base_status["stats"]["class_names"]
                    },
                    "classes": base_status["stats"]["class_names"],
                    "stats": base_status["stats"],
                    "storage_mode": True
                }
        except Exception as e:
            logger.warning(f"获取基础数据集状态失败: {e}")
            pass

    # 原有代码...
    path = dataset_manager.get_active_dataset_path()
    if not path:
        return {"active": False, "message": "未选择数据集", "suggestion": "基础数据集可用，请调用 /api/datasets/default/switch 切换"}
    # ... 其余不变
    active_info = dataset_manager.datasets.get(active_id)
    stats = dict((active_info.stats if active_info else {}) or {})
    train_count = stats.get("train", stats.get("train_images", 0))
    val_count = stats.get("val", stats.get("val_images", 0))
    total_count = stats.get("total", train_count + val_count)

    class_names: list[str] = []
    classes_file = path / "classes.txt"
    if classes_file.exists():
        try:
            class_names = [line.strip() for line in classes_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as class_err:
            logger.warning(f"read active dataset classes failed | dataset_id={active_id} | err={class_err}")

    return {
        "active": True,
        "dataset_id": active_id,
        "dataset_name": active_info.name if active_info else active_id,
        "local_path": str(path),
        "storage_path": f"storage://datasets/{active_info.storage_prefix}" if active_info and active_info.storage_prefix else None,
        "classes": class_names,
        "stats": {
            **stats,
            "train": train_count,
            "val": val_count,
            "total": total_count,
            "classes": len(class_names),
            "class_names": class_names,
        },
        "storage_mode": False,
    }


@app.get("/api/datasets/{dataset_id}/status")
async def get_dataset_status(dataset_id: str):
    """获取指定数据集的状态"""

    # 处理 undefined 或空值
    if not dataset_id or dataset_id.lower() in ("undefined", "null", "none", ""):
        dataset_id = "default"
        logger.info(f"状态查询时 dataset_id 为 undefined，自动回退到 default")

    # 处理 default / base 基础数据集：从 Supabase Storage 读取
    if dataset_id == "default":
        return await _get_base_dataset_status_from_storage()
    if dataset_id == "base":
        return await _get_storage_dataset_status("base", "base", "基础数据集")

    info = dataset_manager.datasets.get(dataset_id)
    if info:
        local_path = info.local_path if info.local_path and info.local_path.exists() else None
        if not local_path and info.storage_prefix:
            return await _get_storage_dataset_status(dataset_id, info.storage_prefix, info.name)
        stats = dict(info.stats or {})
        train_count = stats.get("train", stats.get("train_images", 0))
        val_count = stats.get("val", stats.get("val_images", 0))
        total_count = stats.get("total", train_count + val_count)

        class_names: list[str] = []
        if local_path:
            classes_file = local_path / "classes.txt"
            if classes_file.exists():
                try:
                    class_names = [
                        line.strip()
                        for line in classes_file.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                except Exception as class_err:
                    logger.warning(f"read classes.txt failed | dataset_id={dataset_id} | err={class_err}")

        return {
            "dataset_id": dataset_id,
            "dataset_name": info.name,
            "exists": bool(total_count > 0 or local_path or info.storage_prefix),
            "cached": bool(local_path),
            "cache_path": str(local_path) if local_path else None,
            "stats": {
                **stats,
                "train": train_count,
                "val": val_count,
                "total": total_count,
                "classes": len(class_names),
                "class_names": class_names,
            },
            "is_active": dataset_manager.active_dataset_id == dataset_id,
            "storage_mode": bool(info.storage_prefix) and not bool(local_path),
        }

    try:
        db_dataset_result = supabase.table("datasets").select("*").eq("dataset_id", dataset_id).maybe_single().execute()
        db_dataset = db_dataset_result.data if db_dataset_result else None
    except Exception as db_lookup_err:
        logger.warning(f"lookup dataset status from db failed | dataset_id={dataset_id} | err={db_lookup_err}")
        db_dataset = None

    if db_dataset:
        stats = db_dataset.get("stats") or {}
        cached = dataset_cache_manager.is_cached(dataset_id)
        cache_path = dataset_cache_manager.get_cache_path(dataset_id)
        return {
            "dataset_id": dataset_id,
            "dataset_name": db_dataset.get("name") or dataset_id,
            "exists": True,
            "cached": cached,
            "cache_path": str(cache_path) if cached else None,
            "stats": stats,
            "is_active": dataset_manager.active_dataset_id == dataset_id,
            "storage_mode": not cached,
        }

    raise HTTPException(404, detail=f"数据集 {dataset_id} 不存在")

    info = dataset_manager.datasets.get(dataset_id)
    if False and not info:
        raise HTTPException(404, detail=f"数据集 {dataset_id} 不存在")
    # ... 原有代码不变


# 在 main.py 中，找到你添加的 _get_base_dataset_status_from_storage 函数
# 修改为：



async def _get_base_dataset_status_from_storage(max_files_per_folder: int = 1000) -> dict:
    """
    从 Supabase Storage 的 datasets bucket 读取基础数据集状态
    修复：使用正确的分页参数获取完整文件列表
    """
    return await _get_storage_dataset_status("base", "base", "基础数据集")

    try:
        bucket = "datasets"
        supabase_client = get_supabase_client()

        # ========== 第一步：尝试从数据库获取准确的统计信息 ==========
        try:
            db_result = supabase.table("datasets").select("*").eq("dataset_id", "default").execute()
            if db_result.data and len(db_result.data) > 0:
                db_record = db_result.data[0]
                db_stats = db_record.get("stats", {})
                if db_stats and db_stats.get("total", 0) > 0:
                    logger.info(f"从数据库获取基础数据集统计: train={db_stats.get('train')}, val={db_stats.get('val')}")
                    return {
                        "dataset_id": "default",
                        "dataset_name": db_record.get("name", "基础数据集"),
                        "exists": True,
                        "cached": True,
                        "cache_path": f"storage://{bucket}/",
                        "stats": {
                            "train": db_stats.get("train", 0),
                            "val": db_stats.get("val", 0),
                            "total": db_stats.get("total", 0),
                            "classes": db_stats.get("classes", 0),
                            "class_names": db_stats.get("class_names", []),
                            "train_has_more": False,
                            "val_has_more": False,
                            "max_counted": db_stats.get("total", 0)
                        },
                        "is_active": True,
                        "storage_mode": True
                    }
        except Exception as db_err:
            logger.warning(f"从数据库获取基础数据集统计失败: {db_err}")

        # ========== 第二步：尝试从 dataset_registry 内存缓存获取 ==========
        if "default" in dataset_registry:
            registry_info = dataset_registry["default"]
            registry_stats = registry_info.get("stats", {})
            if registry_stats and registry_stats.get("total", 0) > 0:
                logger.info(f"从内存缓存获取基础数据集统计: train={registry_stats.get('train')}, val={registry_stats.get('val')}")
                return {
                    "dataset_id": "default",
                    "dataset_name": "基础数据集",
                    "exists": True,
                    "cached": True,
                    "cache_path": f"storage://{bucket}/",
                    "stats": {
                        "train": registry_stats.get("train", 0),
                        "val": registry_stats.get("val", 0),
                        "total": registry_stats.get("total", 0),
                        "classes": registry_stats.get("classes", 0),
                        "class_names": registry_stats.get("class_names", []),
                        "train_has_more": False,
                        "val_has_more": False,
                        "max_counted": registry_stats.get("total", 0)
                    },
                    "is_active": True,
                    "storage_mode": True
                }

        # ========== 第三步：使用正确的分页从 Storage 统计 ==========
        def count_images_with_pagination(folder_path: str) -> int:
            """分页统计图片数量，返回 (数量, 是否有更多)"""
            try:
                offset = 0
                limit = 100
                total_count = 0
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif'}

                while True:
                    items = supabase_client.storage.from_(bucket).list(
                        folder_path,
                        {
                            "limit": limit,
                            "offset": offset,
                            "sortBy": {"column": "name", "order": "asc"}
                        }
                    )

                    if not items:
                        break

                    for f in items:
                        name = f.get('name', '').lower()
                        if any(name.endswith(ext) for ext in image_extensions):
                            total_count += 1

                    # 如果达到最大统计限制，标记有更多

                    # 如果返回数量小于 limit，说明已经取完
                    if len(items) < limit:
                        break

                    offset += limit

                return total_count
            except Exception as e:
                logger.warning(f"统计 {folder_path} 失败: {e}")
                return 0

        train_count = count_images_with_pagination("train/images")
        val_count = count_images_with_pagination("val/images")

        # 读取 classes.txt
        classes = []
        try:
            file_response = supabase_client.storage.from_(bucket).download("classes.txt")
            if file_response:
                content = file_response.decode('utf-8') if isinstance(file_response, bytes) else file_response
                classes = [line.strip() for line in content.split('') if line.strip()]
        except Exception as e:
            logger.warning(f"读取 classes.txt 失败: {e}")

        total = train_count + val_count

        return {
            "dataset_id": "default",
            "dataset_name": "基础数据集",
            "exists": total > 0,
            "cached": total > 0,
            "cache_path": f"storage://{bucket}/",
            "stats": {
                "train": train_count,
                "val": val_count,
                "total": total,
                "classes": len(classes),
                "class_names": classes,
                "train_has_more": False,
                "val_has_more": False,
                "max_counted": total
            },
            "is_active": True,
            "storage_mode": True
        }

    except Exception as e:
        logger.error(f"获取基础数据集状态失败: {e}")
        raise HTTPException(500, detail=f"获取基础数据集状态失败: {str(e)}")



@app.post("/api/datasets/{dataset_id}/prepare")
async def prepare_dataset(dataset_id: str, background_tasks: BackgroundTasks):
    """预下载数据集到本地缓存"""
    info = dataset_manager.datasets.get(dataset_id)
    if not info:
        raise HTTPException(404, detail=f"数据集 {dataset_id} 不存在")

    if dataset_manager.is_cached(dataset_id):
        return {
            "success": True,
            "cached": True,
            "message": "数据集已缓存",
            "path": str(dataset_manager.get_cache_path(dataset_id))
        }

    def do_download():
        dataset_manager.get_dataset_path(dataset_id)

    background_tasks.add_task(do_download)

    return {
        "success": True,
        "cached": False,
        "message": "开始下载数据集到本地缓存",
        "dataset_id": dataset_id
    }


@app.post("/api/datasets/{dataset_id}/cleanup")
async def cleanup_dataset(dataset_id: str):
    """清理数据集本地缓存"""
    dataset_manager.cleanup(dataset_id)
    return {
        "success": True,
        "message": f"已清理数据集 {dataset_id} 的缓存"
    }


# =================================================================

for r in app.routes:
    print("ROUTE:", getattr(r, "methods", None), r.path)

# ========== 启动 ==========
if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("🚀 智能标注系统启动")
    logger.info(f"PyTorch: {torch.__version__}")
    logger.info(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info("=" * 60)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
