from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.config import (
    SUPABASE_PROJECT_FILES_BUCKET,
    SUPABASE_PROJECT_FILES_PUBLIC,
    supabase,
)

from app.db.session import get_db
import logging
logger = logging.getLogger(__name__)
from app.models import Project, ProjectFile
from app.schemas.project_storage import FileOut, ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["project-storage"])

def _build_file_urls(file_record: ProjectFile, request: Request) -> tuple[str, str]:
    download_url = str(request.url_for("download_project_file", file_id=str(file_record.id)))
    if SUPABASE_PROJECT_FILES_PUBLIC and supabase is not None:
        preview_url = supabase.storage.from_(SUPABASE_PROJECT_FILES_BUCKET).get_public_url(
            file_record.storage_path
        )
        return download_url, preview_url

    return download_url, download_url


def _serialize_file(file_record: ProjectFile, request: Request) -> FileOut:
    download_url, preview_url = _build_file_urls(file_record, request)
    payload = {
        "id": file_record.id,
        "project_id": file_record.project_id,
        "filename": file_record.filename,
        "storage_path": file_record.storage_path,
        "storage_backend": "supabase",
        "mime_type": file_record.mime_type,
        "size_bytes": file_record.size_bytes,
        "uploaded_by": file_record.uploaded_by,
        "created_at": file_record.created_at,
        "download_url": download_url,
        "preview_url": preview_url,
        "status": file_record.status,
    }
    return FileOut(**payload)


def _ensure_storage_client():
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase Storage 未配置，无法上传项目文件")
    return supabase.storage.from_(SUPABASE_PROJECT_FILES_BUCKET)


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


@router.post("/{project_id}/files", response_model=FileOut)
def upload_project_file(
    project_id: uuid.UUID,
    request: Request,
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bucket = _ensure_storage_client()
    file_ext = Path(file.filename or "").suffix
    safe_filename = Path(file.filename or "unnamed").name

    storage_name = f"{uuid.uuid4().hex}{file_ext}"
    object_key = f"projects/{project_id}/{storage_name}"
    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        bucket.upload(
            path=object_key,
            file=file_bytes,
            file_options={
                "content-type": file.content_type or "application/octet-stream",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"上传到 Supabase Storage 失败: {exc}") from exc

    file_record = ProjectFile(
        project_id=project_id,
        filename=safe_filename,
        storage_path=object_key,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        uploaded_by=uploaded_by,
        status="pending"  # ✅ 数据库层面记录分类
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return _serialize_file(file_record, request)


@router.get("/{project_id}/files", response_model=list[FileOut])
def list_project_files(project_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    logger.info(f"【FILES-001】查询项目文件列表 | project_id={project_id}")

    # 强制刷新会话
    logger.info(f"【FILES-002】执行db.expire_all()")
    db.expire_all()

    logger.info(f"【FILES-003】执行db.commit()")
    db.commit()

    # 查询文件
    logger.info(f"【FILES-004】查询ProjectFile表")
    file_records = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.created_at.desc())
        .all()
    )

    logger.info(f"【FILES-005】查询结果 | total_files={len(file_records)}")

    # 记录每个文件的状态
    status_summary = {}
    for f in file_records:
        status_summary[f.status] = status_summary.get(f.status, 0) + 1
        logger.info(f"【FILES-006】文件详情 | file_id={f.id}, filename={f.filename}, status={f.status}")

    logger.info(f"【FILES-007】状态统计 | {status_summary}")

    # 序列化并返回
    result = [_serialize_file(file_record, request) for file_record in file_records]
    logger.info(f"【FILES-008】返回文件列表 | count={len(result)}")

    return result

@router.get("/files/{file_id}/download")
def download_project_file(file_id: uuid.UUID, db: Session = Depends(get_db)):
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    bucket = _ensure_storage_client()
    try:
        content = bucket.download(file_record.storage_path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"远端文件不存在或已被删除: {exc}") from exc

    return Response(
        content=content,
        media_type=file_record.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f'inline; filename="{file_record.filename}"'
                if (file_record.mime_type or "").startswith("image/")
                else f'attachment; filename="{file_record.filename}"'
            )
        },
    )

@router.delete("/{project_id}")
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    storage_keys = [file_record.storage_path for file_record in project.files if file_record.storage_path]
    if storage_keys:
        bucket = _ensure_storage_client()
        try:
            bucket.remove(storage_keys)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"删除 Supabase Storage 文件失败: {exc}") from exc

    # 删除数据库记录（会自动级联删除 files）
    db.delete(project)
    db.commit()


    return {"success": True, "message": "项目已删除"}