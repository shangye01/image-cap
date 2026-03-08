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
import torch
from PIL import Image
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from .api import auth
from .config import supabase, SUPABASE_URL, TRAINING_CONFIG

print(f"SUPABASE_URL: {SUPABASE_URL}")  # 加上这行看输出
app = FastAPI()
# 导入配置（相对导入）



# 注册路由
app.include_router(auth.router)  # 这个应该已经可以了，确认 auth.py 里有 router = APIRouter(...)

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== FastAPI 应用 ==========


# CORS - 允许前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
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


def remove_duplicate_annotations(annotations: List[Dict[str, Any]], iou_threshold: float = 0.85) -> List[Dict[str, Any]]:
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

@app.get("/")
def index():
    return {"message": "后端启动成功", "service": "智能标注系统API"}


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


@app.get("/api/tasks")
async def get_tasks(
    project: Optional[str] = None,
    status: Optional[str] = None
):
    """获取任务列表"""
    try:
        query = supabase.table("tasks").select("*")

        if project:
            query = query.eq("project_name", project)
        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()

        return {
            "success": True,
            "tasks": result.data or []
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.post("/api/predict")
async def predict(request: Request, file: UploadFile = File(...)):
    """上传图片 → AI预测 → 返回结果"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="必须是图片文件")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="文件超过10MB限制")

    try:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        file_name = f"uploads/{task_id}.jpg"

        try:
            supabase.storage.from_("images").upload(
                path=file_name,
                file=contents,
                file_options={"content-type": "image/jpeg"}
            )
            image_url = supabase.storage.from_("images").get_public_url(file_name)
            logger.info(f"图片已上传: {image_url}")
        except Exception as storage_err:
            logger.error(f"Storage上传失败: {storage_err}")
            local_path = UPLOAD_DIR / f"{task_id}.jpg"
            with open(local_path, "wb") as f:
                f.write(contents)
            image_url = build_local_upload_url(f"{task_id}.jpg", request)
            file_name = str(local_path)

        task_data = {
            "id": task_id,
            "image_url": image_url,
            "image_storage_path": file_name,
            "status": "annotating",
            "yolo_version": model_manager.active_version
        }
        supabase.table("tasks").insert(task_data).execute()

        model, version = model_manager.get()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        results = model(image, conf=0.25, iou=0.45)

        raw_annotations = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                label = model.names[int(box.cls[0])]
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
        removed_count = len(raw_annotations) - len(annotations)

        if annotations:
            supabase.table("drafts").upsert({
                "task_id": task_id,
                "annotations_json": annotations,
                "user_id": "current_user",
                "saved_at": datetime.now().isoformat()
            }).execute()

        return {
            "success": True,
            "task_id": task_id,
            "image_url": image_url,
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
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail=f"处理失败: {str(e)}")




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
            cloud_result = supabase.table("model_versions").select("*").order("created_at", desc=True).limit(10).execute()
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


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        task = supabase.table("tasks").select("*").eq("id", task_id).single().execute().data
        if not task:
            raise HTTPException(404, detail="任务不存在")

        draft = supabase.table("drafts").select("*").eq("task_id", task_id).maybe_single().execute().data
        if draft:
            return {"task": task, "annotations": draft["annotations_json"], "source": "draft"}

        anns = supabase.table("annotations").select("*").eq("task_id", task_id).execute().data
        return {"task": task, "annotations": anns or [], "source": "database"}
    except Exception as e:
        raise HTTPException(404, detail=str(e))


@app.post("/api/annotations/{task_id}")
async def save_annotations(task_id: str, payload: dict):
    try:
        anns = payload.get("annotations", [])
        is_draft = payload.get("is_draft", True)
        user_id = payload.get("user_id", "anonymous")

        task_check = supabase.table("tasks").select("id").eq("id", task_id).execute()
        if not task_check.data:
            raise HTTPException(404, detail="任务不存在")

        if is_draft:
            supabase.table("drafts").upsert({
                "task_id": task_id,
                "annotations_json": anns,
                "user_id": user_id,
                "saved_at": datetime.now().isoformat()
            }).execute()
            return {"success": True, "status": "draft_saved", "count": len(anns)}
        else:
            supabase.table("drafts").delete().eq("task_id", task_id).execute()
            for ann in anns:
                supabase.table("annotations").insert({
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
                }).execute()

            supabase.table("tasks").update({
                "status": "completed",
                "annotations_count": len(anns),
                "completed_at": datetime.now().isoformat()
            }).eq("id", task_id).execute()

            return {"success": True, "status": "submitted", "count": len(anns)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存失败: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/labels")
async def get_labels():
    try:
        res = supabase.table("label_configs").select("*").order("name").execute()
        return {"labels": res.data or []}
    except:
        return {"labels": []}


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
async def get_local_upload(filename: str):
    path = UPLOAD_DIR / filename
    if path.exists():
        return FileResponse(path)
    raise HTTPException(404, detail="文件不存在")


@app.post("/api/models/{model_name}/upload")
async def upload_specific_model(model_name: str):
    try:
        from urllib.parse import unquote
        model_name = unquote(model_name)

        logger.info(f"尝试上传模型: {model_name}")

        model_path = MODEL_DIR / f"{model_name}.pt"
        if not model_path.exists():
            matching = list(MODEL_DIR.glob(f"*{model_name}*.pt"))
            if matching:
                model_path = matching[0]
                logger.info(f"找到匹配文件: {model_path}")
            else:
                raise HTTPException(404, detail=f"未找到模型文件: {model_name}")

        file_size = model_path.stat().st_size
        logger.info(f"模型大小: {file_size / (1024 * 1024):.1f} MB")

        upload_path = f"weights/{model_path.name}"
        cloud_path = f"models/{upload_path}"

        with open(model_path, "rb") as f:
            try:
                supabase.storage.from_("models").remove([upload_path])
                logger.info("删除已存在的文件")
            except Exception:
                pass

            supabase.storage.from_("models").upload(upload_path, f)
            logger.info(f"上传成功: {cloud_path}")

        try:
            existing = supabase.table("model_versions") \
                .select("*") \
                .eq("version_name", model_path.stem) \
                .execute()

            if existing.data:
                result = supabase.table("model_versions").update({
                    "model_path": cloud_path,
                    "local_path": str(model_path.absolute()),
                    "updated_at": datetime.now().isoformat()
                }).eq("version_name", model_path.stem).execute()
                logger.info(f"数据库记录已更新: {result.data}")
            else:
                result = supabase.table("model_versions").insert({
                    "version_name": model_path.stem,
                    "model_size": "unknown",
                    "model_path": cloud_path,
                    "local_path": str(model_path.absolute()),
                    "is_active": False,
                    "training_status": "completed",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).execute()
                logger.info(f"数据库记录已创建: {result.data}")

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
