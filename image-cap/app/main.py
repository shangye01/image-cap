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
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote
import numpy as np
import urllib.request
import torch

from typing import Optional
from PIL import Image
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query, Form, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from .api import auth
from .api import project_storage
from .db.base import init_db

from .config import supabase, SUPABASE_URL, TRAINING_CONFIG

from app.schemas.project_storage import AnnotationSessionCreate, AnnotationSessionResponse, AnnotationSessionTask
from app.models import ProjectFile, Project
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.project_storage import router as project_router
import uuid
from datetime import datetime
import logging
from fastapi.concurrency import run_in_threadpool
from app.models import User
from app.db.session import SessionLocal
from app.utils.jwt import ALGORITHM, SECRET_KEY
from jose import jwt

logger = logging.getLogger(__name__)
print(f"SUPABASE_URL: {SUPABASE_URL}")  # 加上这行看输出
app = FastAPI()

# 注册路由
app.include_router(auth.router)
app.include_router(project_storage.router)

print("MAIN FILE:", __file__)
print("PROJECT_STORAGE FILE:", project_storage.__file__)


class ProgressConnectionManager:
    """按用户名维度维护 websocket 连接，推送项目进度变化。"""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = threading.Lock()

    async def connect(self, username: str, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(username, set()).add(websocket)

    def disconnect(self, username: str, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(username)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(username, None)

    async def emit_to_users(self, usernames: list[str], payload: dict[str, Any]) -> None:
        targets: list[WebSocket] = []
        with self._lock:
            for username in set(usernames):
                targets.extend(list(self._connections.get(username, set())))

        dead_connections: list[tuple[str, WebSocket]] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead_connections.append((payload.get("owner"), websocket))

        if dead_connections:
            with self._lock:
                for _, ws in dead_connections:
                    for name, sockets in list(self._connections.items()):
                        if ws in sockets:
                            sockets.discard(ws)
                            if not sockets:
                                self._connections.pop(name, None)


progress_ws_manager = ProgressConnectionManager()


def _resolve_ws_username(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            return None
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user.username if user else None
        finally:
            db.close()
    except Exception:
        return None


@app.on_event("startup")
def _startup() -> None:
    init_db()
    auth.ensure_auth_resources()


@app.websocket("/api/ws/progress")
async def progress_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    username = _resolve_ws_username(token)
    if not username:
        await websocket.close(code=1008)
        return

    await progress_ws_manager.connect(username, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_ws_manager.disconnect(username, websocket)
    except Exception:
        progress_ws_manager.disconnect(username, websocket)


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
    def validate() -> Tuple[bool, str, Dict]:
        """验证数据集"""
        train_images = DATASET_DIR / "train" / "images"
        train_labels = DATASET_DIR / "train" / "labels"
        val_images = DATASET_DIR / "val" / "images"
        val_labels = DATASET_DIR / "val" / "labels"

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


def prepare_yaml():
    """生成data.yaml"""
    base = DATASET_DIR.absolute()

    classes_file = base / "classes.txt"
    if classes_file.exists():
        names = [l.strip() for l in open(classes_file) if l.strip()]
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


def run_training(epochs: int, batch: int, model_size: str, use_aug: bool):
    """执行训练（后台任务）"""
    global latest_training_result
    start_time = time.time()

    try:
        logger.info("=" * 60)
        logger.info(f"🚀 开始训练 | 轮数: {epochs} | 批次: {batch}")

        yaml_path = prepare_yaml()
        train_count = len(list((DATASET_DIR / "train" / "images").glob("*")))

        base_model = find_latest_custom_model() or ModelManager.MODEL_SIZES.get(model_size, 'yolov8n.pt')

        if base_model != ModelManager.MODEL_SIZES.get(model_size, 'yolov8n.pt'):
            logger.info(f"🔄 使用上次训练的模型继续训练: {Path(base_model).name}")
        else:
            logger.info(f"🆕 使用预训练模型开始新训练: {base_model}")

        version = generate_version_name()
        logger.info(f"📋 模型版本: {version}")

        model = YOLO(base_model)

        args = {
            "data": yaml_path,
            "epochs": epochs,
            "batch": batch,
            "imgsz": 640,
            "name": version,
            "project": "runs/train",
            "exist_ok": True,
            "patience": 20,
            "save": True,
            "amp": True,
            "optimizer": "AdamW",
            "lr0": 0.001,
            "lrf": 0.01,
            "momentum": 0.937,
            "weight_decay": 0.0005,
            "warmup_epochs": 3,
        }

        if use_aug:
            args.update({
                "degrees": 15.0,
                "translate": 0.2,
                "scale": 0.5,
                "shear": 5.0,
                "flipud": 0.3,
                "fliplr": 0.5,
                "hsv_h": 0.015,
                "hsv_s": 0.7,
                "hsv_v": 0.4,
                "mosaic": 1.0,
                "mixup": 0.1,
            })
            logger.info("✅ 启用数据增强")

        if train_count < 200 and epochs > 20 and base_model.endswith('.pt') and 'custom' not in base_model:
            logger.info("🔒 阶段1: 冻结主干网络预热...")
            model.train(**{**args, "epochs": min(10, epochs // 5), "freeze": 10, "lr0": 0.0005})
            logger.info("🔓 解冻继续训练...")

        results = model.train(**args)

        best_pt = Path(f"runs/train/{version}/weights/best.pt")
        if not best_pt.exists():
            raise FileNotFoundError("未找到训练好的模型文件")

        target = MODEL_DIR / f"{version}.pt"
        shutil.copy(best_pt, target)
        logger.info(f"✅ 模型已保存到本地: {target}")

        best_link = MODEL_DIR / "best.pt"
        last_link = MODEL_DIR / "last.pt"
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

        try:
            supabase.table("model_versions").update({"is_active": False}).neq("id", 0).execute()

            db_result = supabase.table("model_versions").insert({
                "version_name": version,
                "training_data_count": train_count,
                "model_size": model_size,
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
            "local_path": str(target.absolute()),
            "metrics": metrics,
            "uploaded": False,
            "completed_at": datetime.now().isoformat(),
            "duration_hours": training_duration
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

    file_ids = [str(f.id) for f in files_result]

    # 查询对应的任务
    tasks_result = supabase.table("tasks").select("*").in_("file_id", file_ids).execute()
    tasks = tasks_result.data or []

    # 按文件创建时间排序
    file_order = {str(f.id): f.created_at for f in files_result}
    tasks.sort(key=lambda t: file_order.get(t.get("file_id", ""), datetime.min))

    # 构建响应
    task_list = []
    for task in tasks:
        task_list.append({
            "task_id": task["id"],
            "file_id": task.get("file_id"),
            "filename": task.get("filename", ""),
            "image_url": task.get("image_url"),
            "status": task.get("status", "labeling"),
            "project_name": task.get("project_name"),
            "project_id": project_id,
            "use_keywords": task.get("use_keywords", False),
            "keywords": task.get("keywords", []),
            "annotations": task.get("annotations", [])
        })

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

    # 验证文件存在
    file_record = db.query(ProjectFile).filter(
        ProjectFile.id == file_id,
        ProjectFile.project_id == project_id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 查询任务
    task_result = supabase.table("tasks").select("*").eq("file_id", file_id).maybe_single().execute()

    if not task_result or not task_result.data:  # ✅ 修复：检查 task_result 是否为 None
        return {"task": None}

    task = task_result.data

    # 查询草稿或标注
    annotations = []
    if task.get("status") == "completed":
        anns_result = supabase.table("annotations").select("*").eq("task_id", task["id"]).execute()
        annotations = anns_result.data or [] if anns_result else []  # ✅ 同样检查 None
    else:
        draft_result = supabase.table("drafts").select("*").eq("task_id", task["id"]).maybe_single().execute()
        # ✅ 修复：检查 draft_result 是否为 None
        if draft_result and draft_result.data:
            annotations = draft_result.data.get("annotations_json", [])

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

    return {"task": task_obj}


@app.get("/api/projects/{project_id}/tasks/{task_id}/adjacent")
async def get_adjacent_task(
        project_id: str,
        task_id: str,
        direction: str = Query(..., regex="^(next|prev)$"),
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
    annotations = []
    if target_task.get("status") == "completed":
        anns_result = supabase.table("annotations").select("*").eq("task_id", target_task["id"]).execute()
        annotations = anns_result.data or []
    else:
        draft_result = supabase.table("drafts").select("*").eq("task_id", target_task["id"]).maybe_single().execute()
        if draft_result.data:
            annotations = draft_result.data.get("annotations_json", [])

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
            "annotations": task.get("annotations", [])
        })

    logger.info(f"【ALL-LABELING】返回 {len(task_list)} 个标注中任务")
    return {"tasks": task_list, "total": len(task_list)}
@app.get("/")
def index():
    return {"message": "后端启动成功", "service": "智能标注系统API"}


@app.post("/api/predict")
async def predict_image(
        file: UploadFile = File(...),
        keywords: Optional[str] = Form(None)
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

        # 运行模型
        model, version = model_manager.get()
        results = model(image, conf=0.25, iou=0.45)

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
        logger.error(f"通用预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================= 新增：预标注生成与任务分发 =================
from fastapi.concurrency import run_in_threadpool


@app.post("/api/projects/{project_id}/sessions", response_model=AnnotationSessionResponse)
async def create_annotation_session(
        project_id: str,
        payload: AnnotationSessionCreate,
        db: Session = Depends(get_db)
):
    """创建标注会话，生成项目名_序号格式的任务ID，防止重复创建
    对于已有标注的文件，直接返回已有标注，不再进行AI预测"""
    target_keywords = [k.strip().lower() for k in payload.keywords] if payload.keywords else []
    bucket = supabase.storage.from_("project-files")

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
                task_id=None
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
                    "user_id": "current_user",
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


@app.post("/api/tasks/{task_id}/smart-annotate")
async def smart_annotate_incremental(
        task_id: str,
        payload: dict
):
    """
    增量式智能预标注：检测新物体，只添加不与已有标注重叠的框
    """
    try:
        logger.info(f"【SMART-ANNOTATE】开始增量预标注 | task_id={task_id}")

        # 获取任务信息
        task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task_res.data:
            raise HTTPException(404, detail="任务不存在")

        task = task_res.data[0]
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
                    "user_id": "current_user",
                    "saved_at": datetime.now().isoformat()
                }).execute()
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
async def move_to_done(project_id: str, payload: dict, db: Session = Depends(get_db)):
    """前端点击「提交标注」后触发：将数据库中的文件状态更为已标注"""
    task_id = payload.get("taskId")

    # 验证任务存在
    task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(404, detail=f"任务 {task_id} 不存在")

    task_data = task_res.data[0]
    storage_path = task_data.get("image_storage_path")

    updated_rows = 0
    notify_usernames: set[str] = set()
    # ✅ 修复：更新文件状态为 done，并同步到同源分享项目
    if storage_path:
        project_uuid = uuid.UUID(project_id)
        current_project = db.query(Project).filter(Project.id == project_uuid).first()
        related_project_ids = [project_id]
        if current_project:
            root_project_id = current_project.source_project_id or current_project.id
            sibling_projects = (
                db.query(Project.id, Project.owner_id)
                .filter((Project.id == root_project_id) | (Project.source_project_id == root_project_id))
                .all()
            )
            related_project_ids = [item[0] for item in sibling_projects] or [project_uuid]
            notify_usernames = {item[1] for item in sibling_projects if item[1]}

        matched_files = (
            db.query(ProjectFile)
            .filter(
                ProjectFile.storage_path == storage_path,
                ProjectFile.project_id.in_(related_project_ids),
            )
            .all()
        )

        for project_file in matched_files:
            if project_file.status != "done":
                project_file.status = "done"
                updated_rows += 1

        if matched_files:
            db.commit()
            logger.info(f"文件状态已同步为 done | storage_path={storage_path}, updated={updated_rows}")
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
        else:
            logger.warning(f"未找到对应的文件记录: {storage_path}")

    # ✅ 修复：更新任务状态为 completed
    supabase.table("tasks").update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "annotations_count": task_data.get("annotations_count", 0)
    }).eq("id", task_id).execute()

    logger.info(f"任务 {task_id} 已完成")

    return {"success": True, "message": "任务已完成", "task_id": task_id}


# =================================================================
# ========== 公共预测函数 ==========
async def run_prediction(
        image_data: bytes,
        keywords: Optional[List[str]] = None,
        save_draft: bool = False,
        task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    运行AI预测，返回标注结果
    被 /api/predict 和 /api/projects/{project_id}/sessions 共用
    """
    try:
        # 加载图片
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # 运行模型
        model, version = model_manager.get()
        results = model(image, conf=0.25, iou=0.45)

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
                    "user_id": "current_user",
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

            # 运行模型
            model, version = model_manager.get()
            results = model(image, conf=0.25, iou=0.45)

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
                        "user_id": "current_user",
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
            supabase.table("annotations").insert(ann_data).execute()

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
            return {
                "task": task,
                "annotations": draft["annotations_json"],
                "source": "draft"
            }

        # 查询已提交标注
        anns_result = supabase.table("annotations").select("*").eq("task_id", task_id).execute()
        anns = anns_result.data or []

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
        epochs: int = Query(default=100, ge=10, le=500),
        batch: int = Query(default=16, ge=1, le=64),
        model_size: str = Query(default="auto", regex="^(auto|n|s|m|l|x)$"),
        augmentation: bool = Query(default=True),
        background_tasks: BackgroundTasks = None
):
    """启动训练"""
    try:
        is_valid, msg, details = DatasetValidator.validate()
        if not is_valid:
            raise HTTPException(400, detail=f"数据集未准备好: {msg}")

        train_count = details["stats"]["train"]

        if model_size == "auto":
            model_size = model_manager.select_size(train_count)

        background_tasks.add_task(
            run_training,
            epochs=epochs,
            batch=batch,
            model_size=model_size,
            use_aug=augmentation
        )

        return {
            "success": True,
            "message": "训练已启动",
            "config": {
                "epochs": epochs,
                "batch": batch,
                "model_size": model_size,
                "train_count": train_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


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
async def save_annotations(task_id: str, payload: dict):
    """保存标注，支持 项目名_序号 格式"""
    try:
        anns = payload.get("annotations", [])
        is_draft = payload.get("is_draft", True)
        user_id = payload.get("user_id", "anonymous")

        logger.info(f"保存标注: task_id={task_id}, is_draft={is_draft}, count={len(anns)}")

        # 验证任务存在
        task_check = supabase.table("tasks").select("id,project_name").eq("id", task_id).execute()
        if not task_check.data:
            raise HTTPException(404, detail=f"任务不存在: {task_id}")

        project_name = task_check.data[0].get("project_name", "unknown")

        if is_draft:
            # 保存草稿
            supabase.table("drafts").upsert({
                "task_id": task_id,
                "annotations_json": anns,
                "user_id": user_id,
                "saved_at": datetime.now().isoformat()
            }).execute()
            return {"success": True, "status": "draft_saved", "count": len(anns)}
        else:
            # 提交最终标注
            supabase.table("drafts").delete().eq("task_id", task_id).execute()

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
                supabase.table("annotations").insert(annotations_data).execute()

            # 更新任务状态为已完成
            supabase.table("tasks").update({
                "status": "completed",
                "annotations_count": len(anns),
                "completed_at": datetime.now().isoformat()
            }).eq("id", task_id).execute()

            return {
                "success": True,
                "status": "submitted",
                "count": len(anns),
                "project_name": project_name,
                "task_id": task_id
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