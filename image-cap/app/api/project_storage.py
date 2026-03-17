from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, ProjectFile
from app.schemas.project_storage import FileOut, ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["project-storage"])

UPLOAD_ROOT = Path("./uploads/projects")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


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
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project_dir = UPLOAD_ROOT / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

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