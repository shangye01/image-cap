from __future__ import annotations

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
import shutil
import uuid
import httpx
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, ProjectFile
from app.config import supabase
from app.schemas.project_storage import (
    FileOut,
    ProjectCreate,
    ProjectOut,
    AnnotationSessionCreate
)

router = APIRouter(prefix="/api/projects", tags=["project-storage"])

UPLOAD_ROOT = Path("./uploads/projects")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
TASK_META_FILENAME = "annotation_tasks.json"


# ========== Helper Functions ==========
def _project_root(project_id: uuid.UUID) -> Path:
    return UPLOAD_ROOT / str(project_id)


def _folder_path(project_id: uuid.UUID, folder_name: str) -> Path:
    path = _project_root(project_id) / folder_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _task_meta_path(project_id: uuid.UUID) -> Path:
    return _project_root(project_id) / TASK_META_FILENAME


def _load_task_meta(project_id: uuid.UUID) -> dict:
    meta_path = _task_meta_path(project_id)
    if not meta_path.exists():
        return {"tasks": [], "updated_at": None, "task_counter": 0}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": [], "updated_at": None, "task_counter": 0}


def _save_task_meta(project_id: uuid.UUID, payload: dict) -> None:
    project_root = _project_root(project_id)
    project_root.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.utcnow().isoformat()
    _task_meta_path(project_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _generate_task_id(project_name: str, existing_counter: int) -> str:
    """生成项目名_001格式的任务ID"""
    safe_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in project_name.strip())
    safe_name = safe_name[:20]  # 限制长度
    if not safe_name:
        safe_name = "project"
    return f"{safe_name}_{existing_counter + 1:03d}"


# ========== Annotation Session Routes ==========
@router.post("/{project_id}/annotation-session")
async def create_annotation_session(
        project_id: str,
        session_data: AnnotationSessionCreate,
        db: Session = Depends(get_db)
):
    """
    创建标注会话：
    1. 生成项目名_001格式的任务ID
    2. 移动文件到"标注中"文件夹
    3. 调用智能预标注接口生成annotations
    4. 返回包含预标注结果的任务数据
    """
    # 1. 验证项目
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 2. 验证文件
    files = db.query(ProjectFile).filter(
        ProjectFile.id.in_(session_data.file_ids),
        ProjectFile.project_id == project_id
    ).all()

    if len(files) != len(session_data.file_ids):
        raise HTTPException(status_code=400, detail="部分文件不存在或不属于该项目")

    project_uuid = uuid.UUID(project_id)

    # 3. 准备目录
    pending_dir = _folder_path(project_uuid, "待标注")
    labeling_dir = _folder_path(project_uuid, "标注中")
    done_dir = _folder_path(project_uuid, "已标注")

    # 4. 获取当前任务计数器（用于生成001,002...）
    meta = _load_task_meta(project_uuid)
    task_counter = meta.get("task_counter", 0)

    # 5. 生成任务并调用预标注
    tasks = []
    keywords = session_data.keywords if session_data.use_keywords else []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for index, file in enumerate(files):
            task_counter += 1
            task_id = _generate_task_id(project.name, task_counter - 1)

            # 移动文件：待标注 -> 标注中
            source_path = Path(file.storage_path)
            current_folder = "待标注"

            # 判断当前文件位置
            if "标注中" in str(source_path):
                current_folder = "标注中"
            elif "已标注" in str(source_path):
                current_folder = "已标注"

            # 只有从待标注移动时才实际移动文件
            new_storage_path = str(source_path)
            if current_folder == "待标注" and source_path.exists():
                try:
                    destination = labeling_dir / source_path.name
                    if destination != source_path:
                        shutil.move(str(source_path), str(destination))
                        new_storage_path = str(destination)
                        # 更新数据库中的路径
                        file.storage_path = new_storage_path
                        db.commit()
                except Exception as e:
                    print(f"移动文件失败: {e}")

            # 构建图片URL
            image_url = f"/api/projects/files/{file.id}/download"

            # 调用智能预标注接口
            annotations = []
            try:
                # 调用本地的 predict 接口（关键词模式）
                predict_payload = {"keywords": keywords} if session_data.use_keywords else {}

                # 方式1：如果文件已在标注中，使用 task predict 接口
                # 先创建临时任务记录用于预测
                resp = await client.post(
                    f"http://localhost:8000/api/projects/files/{file.id}/predict",
                    json=predict_payload
                )

                if resp.status_code == 200:
                    predict_data = resp.json()
                    annotations = predict_data.get("annotations", [])
                    print(f"文件 {file.filename} 预标注成功，检测到 {len(annotations)} 个目标")
                else:
                    print(f"预标注请求失败: {resp.status_code}")

            except Exception as e:
                print(f"调用预标注接口失败: {e}")
                # 预标注失败不影响任务创建，只是annotations为空

            # 构建任务数据
            task = {
                "task_id": task_id,
                "file_id": str(file.id),
                "filename": file.filename,
                "storage_path": new_storage_path,
                "image_url": image_url,
                "project_id": project_id,
                "project_name": project.name,
                "use_keywords": session_data.use_keywords,
                "keywords": keywords,
                "status": "annotating" if index == 0 else "pending",
                "annotations": annotations  # 包含预标注结果
            }
            tasks.append(task)

            # 同步到supabase（如果配置了）
            if supabase is not None:
                try:
                    supabase.table("tasks").upsert({
                        "id": task_id,
                        "image_url": image_url,
                        "status": task["status"],
                        "annotations_count": len(annotations),
                        "created_at": datetime.utcnow().isoformat(),
                    }).execute()
                except Exception as e:
                    print(f"Supabase同步失败: {e}")

    if not tasks:
        raise HTTPException(status_code=400, detail="没有有效的文件可以创建标注任务")

    # 6. 保存元数据（更新计数器）
    existing_tasks = meta.get("tasks", [])
    for task in tasks:
        # 移除旧任务（如果存在相同task_id）
        existing_tasks = [item for item in existing_tasks if item.get("task_id") != task["task_id"]]
        existing_tasks.append(task)

    meta["tasks"] = existing_tasks
    meta["task_counter"] = task_counter
    _save_task_meta(project_uuid, meta)

    # 7. 返回前端期望的数据结构
    return {
        "success": True,
        "project_id": project_id,
        "project_name": project.name,
        "use_keywords": session_data.use_keywords,
        "keywords": keywords,
        "tasks": tasks,
        "first_task": tasks[0]
    }


# 为单个文件添加预测端点（避免循环导入问题）
@router.post("/files/{file_id}/predict")
async def predict_single_file(
        file_id: str,
        payload: dict = {},
        db: Session = Depends(get_db)
):
    """对单个项目文件进行智能预标注"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = Path(file_record.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    keywords = payload.get("keywords", [])
    target_keywords = [k.strip().lower() for k in keywords] if keywords else []

    try:
        # 延迟导入避免循环导入
        import torch
        from PIL import Image
        from ultralytics import YOLO

        # 尝试加载模型（简化版，实际应从main.py共享）
        model_path = "./models/best.pt"
        if not os.path.exists(model_path):
            model_path = "yolov8n.pt"  # 默认模型

        model = YOLO(model_path)

        # 预测
        image = Image.open(file_path).convert("RGB")
        results = model(image, conf=0.25, iou=0.45)

        annotations = []
        for r in results:
            for box in r.boxes:
                label = model.names[int(box.cls[0])]

                # 关键词过滤
                if target_keywords and label.lower() not in target_keywords:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # 简单颜色映射
                color_map = {
                    'person': '#ff0000', 'car': '#0000ff', 'dog': '#00ff00',
                    'cat': '#ffa500', 'bird': '#ffff00'
                }
                color = color_map.get(label.lower(), '#3b82f6')

                annotations.append({
                    "id": f"ann_{uuid.uuid4().hex[:6]}",
                    "label": label,
                    "x": round(max(0, x1), 2),
                    "y": round(max(0, y1), 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 3),
                    "color": color
                })

        # 去重（简单IOU去重）
        final_annotations = _remove_duplicates(annotations)

        return {
            "success": True,
            "file_id": file_id,
            "annotations": final_annotations,
            "message": f"检测到 {len(final_annotations)} 个目标"
        }

    except Exception as e:
        print(f"预测失败: {e}")
        return {
            "success": False,
            "file_id": file_id,
            "annotations": [],
            "message": str(e)
        }


def _remove_duplicates(annotations: list, iou_threshold: float = 0.85) -> list:
    """简单的IOU去重"""
    if len(annotations) <= 1:
        return annotations

    def calc_iou(box1, box2):
        x1 = max(box1['x'], box2['x'])
        y1 = max(box1['y'], box2['y'])
        x2 = min(box1['x'] + box1['width'], box2['x'] + box2['width'])
        y2 = min(box1['y'] + box1['height'], box2['y'] + box2['height'])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = box1['width'] * box1['height']
        area2 = box2['width'] * box2['height']
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    # 按置信度排序
    sorted_anns = sorted(annotations, key=lambda x: x.get('confidence', 0), reverse=True)
    keep = []

    for i, current in enumerate(sorted_anns):
        should_keep = True
        for kept in keep:
            if calc_iou(current, kept) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(current)

    return keep


@router.get("/{project_id}/annotation-session/{task_id}")
async def get_annotation_session_task(
        project_id: uuid.UUID,
        task_id: str
):
    """获取特定任务的标注会话信息"""
    meta = _load_task_meta(project_id)
    task = next(
        (item for item in meta.get("tasks", []) if item.get("task_id") == task_id),
        None
    )

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {"success": True, "task": task}


# ========== Project Routes ==========
@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    existed = db.query(Project).filter(Project.name == payload.name).first()
    if existed:
        raise HTTPException(status_code=409, detail="项目名称已存在")

    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    project = Project(**payload_data)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(owner_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Project).order_by(Project.created_at.desc())
    if owner_id:
        query = query.filter(Project.owner_id == owner_id)
    return query.all()


@router.delete("/{project_id}")
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    db.delete(project)
    db.commit()

    project_dir = UPLOAD_ROOT / str(project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)

    return {"success": True, "message": "项目已删除"}


# ========== File Routes ==========
@router.post("/{project_id}/files", response_model=FileOut)
def upload_project_file(
        project_id: uuid.UUID,
        uploaded_by: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project_dir = _folder_path(project_id, "待标注")

    file_ext = Path(file.filename).suffix
    storage_name = f"{uuid.uuid4().hex}{file_ext}"
    local_path = project_dir / storage_name

    with local_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_record = ProjectFile(
        project_id=project_id,
        filename=file.filename,
        storage_path=str(local_path),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=local_path.stat().st_size,
        uploaded_by=uploaded_by,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


@router.get("/{project_id}/files", response_model=list[FileOut])
def list_project_files(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.created_at.desc())
        .all()
    )


@router.get("/files/{file_id}/download")
def download_project_file(file_id: uuid.UUID, db: Session = Depends(get_db)):
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = Path(file_record.storage_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    return FileResponse(
        path=file_path,
        filename=file_record.filename,
        media_type=file_record.mime_type or "application/octet-stream",
    )