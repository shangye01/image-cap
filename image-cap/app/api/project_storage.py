from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import SUPABASE_PROJECT_FILES_BUCKET, SUPABASE_PROJECT_FILES_PUBLIC, supabase
from app.db.session import get_db
from app.models import Organization, Project, ProjectFile, User, UserOrganization
from app.schemas.project_storage import FileOut, ProjectCreate, ProjectOut, ProjectShareCreate
from app.utils.jwt import ALGORITHM, SECRET_KEY
from jose import jwt

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


def _serialize_project(project: Project) -> ProjectOut:
    return ProjectOut.model_validate(project)


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
    return _serialize_project(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(owner_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Project).order_by(Project.shared_at.desc().nullslast(), Project.created_at.desc())
    if owner_id:
        query = query.filter(Project.owner_id == owner_id)
    return [_serialize_project(project) for project in query.all()]


@router.post("/{project_id}/share")
def share_project(
    project_id: uuid.UUID,
    payload: ProjectShareCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.owner_id != user.username:
        raise HTTPException(status_code=403, detail="仅项目拥有者可以分享项目")

    organization = (
        db.query(Organization)
        .join(UserOrganization, UserOrganization.organization_id == Organization.id)
        .filter(Organization.nickname == payload.organization_nickname, UserOrganization.user_id == user.id)
        .first()
    )
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在或你尚未加入该组织")

    memberships = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == organization.id,
            UserOrganization.user_id.in_(payload.recipient_ids),
        )
        .all()
    )
    membership_map = {membership.user_id: membership for membership in memberships}
    if len(membership_map) != len(set(payload.recipient_ids)):
        raise HTTPException(status_code=400, detail="所选成员必须属于当前组织")

    existing_copies = (
        db.query(Project)
        .filter(Project.source_project_id == project.id, Project.owner_id.in_([m.user.username for m in memberships]))
        .all()
    )
    existing_by_owner = {item.owner_id: item for item in existing_copies}

    copied_to = []
    for membership in memberships:
        recipient = membership.user
        copied_name = f"[分享] {project.name} - {recipient.username}"
        existing_copy = existing_by_owner.get(recipient.username)
        if existing_copy:
            existing_copy.description = project.description
            existing_copy.share_message = payload.message
            existing_copy.shared_by = user.username
            existing_copy.shared_at = datetime.utcnow()
            existing_copy.organization_nickname = payload.organization_nickname
            existing_copy.share_accepted_at = None
            copied_project = existing_copy
            db.query(ProjectFile).filter(ProjectFile.project_id == existing_copy.id).delete()
        else:
            copied_project = Project(
                name=copied_name,
                description=project.description,
                owner_id=recipient.username,
                source_project_id=project.id,
                is_shared_copy=True,
                shared_by=user.username,
                shared_at=datetime.utcnow(),
                share_message=payload.message,
                organization_nickname=payload.organization_nickname,
                share_accepted_at=None,
            )
            db.add(copied_project)
            db.flush()

        for source_file in project.files:
            db.add(
                ProjectFile(
                    project_id=copied_project.id,
                    filename=source_file.filename,
                    storage_path=source_file.storage_path,
                    mime_type=source_file.mime_type,
                    size_bytes=source_file.size_bytes,
                    uploaded_by=user.username,
                    status=source_file.status,
                )
            )

        copied_to.append({"user_id": recipient.id, "username": recipient.username, "project_id": copied_project.id})

    db.commit()
    return {"message": "项目分享成功", "copied_to": copied_to}


@router.post("/{project_id}/accept-share")
def accept_shared_project(
    project_id: uuid.UUID,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not project.is_shared_copy:
        return {"message": "当前项目不是分享副本", "accepted_at": None}
    if project.owner_id != user.username:
        raise HTTPException(status_code=403, detail="仅项目接收者可以确认接收")

    if not project.share_accepted_at:
        project.share_accepted_at = datetime.utcnow()
        db.commit()
        db.refresh(project)

    return {"message": "已确认接收分享项目", "accepted_at": project.share_accepted_at}


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
        status="pending",
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return _serialize_file(file_record, request)


@router.get("/{project_id}/files", response_model=list[FileOut])
def list_project_files(project_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    file_records = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.created_at.desc())
        .all()
    )
    return [_serialize_file(file_record, request) for file_record in file_records]


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
    if storage_keys and not project.is_shared_copy:
        other_file_count = (
            db.query(ProjectFile)
            .filter(ProjectFile.storage_path.in_(storage_keys), ProjectFile.project_id != project.id)
            .count()
        )
        if other_file_count == 0:
            bucket = _ensure_storage_client()
            try:
                bucket.remove(storage_keys)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"删除 Supabase Storage 文件失败: {exc}") from exc

    db.delete(project)
    db.commit()


    return {"success": True, "message": "项目已删除"}