from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from unicodedata import normalize
from urllib.parse import quote

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


def _build_assignment_map(
    source_files: list[ProjectFile], recipient_user_ids: list[str], share_mode: str
) -> dict[str, set[uuid.UUID]]:
    assignment_map: dict[str, set[uuid.UUID]] = {user_id: set() for user_id in recipient_user_ids}
    if not source_files or not recipient_user_ids:
        return assignment_map

    if share_mode == "single":
        for idx, source_file in enumerate(source_files):
            user_id = recipient_user_ids[idx % len(recipient_user_ids)]
            assignment_map[user_id].add(source_file.id)
        return assignment_map

    if len(recipient_user_ids) < 3:
        raise HTTPException(status_code=400, detail="协作标注至少需要选择 3 位成员")

    for idx, source_file in enumerate(source_files):
        base = idx % len(recipient_user_ids)
        selected = {
            recipient_user_ids[base],
            recipient_user_ids[(base + 1) % len(recipient_user_ids)],
            recipient_user_ids[(base + 2) % len(recipient_user_ids)],
        }
        for user_id in selected:
            assignment_map[user_id].add(source_file.id)
    return assignment_map


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


def _build_content_disposition(filename: str, disposition_type: str) -> str:
    ascii_fallback = normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = "download"
    ascii_fallback = ascii_fallback.replace("\\", "_").replace('"', "_")
    encoded_filename = quote(filename, safe="")
    return f'{disposition_type}; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_filename}'


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


@router.get("/task-center/overview")
def get_task_center_overview(owner_id: str, db: Session = Depends(get_db)):
    """
    任务数据中心聚合接口：
    - 按 owner_id 获取项目
    - 基于项目文件状态关联 Supabase tasks
    - 返回前端任务中心所需的统一任务结构
    """
    projects = (
        db.query(Project)
        .filter(Project.owner_id == owner_id)
        .order_by(Project.created_at.desc())
        .all()
    )

    all_tasks: list[dict] = []

    for project in projects:
        files = (
            db.query(ProjectFile)
            .filter(ProjectFile.project_id == project.id)
            .order_by(ProjectFile.created_at.asc())
            .all()
        )
        if not files:
            continue

        file_by_id = {str(file.id): file for file in files}
        file_ids = list(file_by_id.keys())
        task_by_file_id: dict[str, dict] = {}

        # 避免 in_ 过长，按块查询
        chunk_size = 200
        for idx in range(0, len(file_ids), chunk_size):
            batch_ids = file_ids[idx : idx + chunk_size]
            result = supabase.table("tasks").select("*").in_("file_id", batch_ids).execute()
            for task in (result.data or []):
                task_file_id = task.get("file_id")
                if not task_file_id:
                    continue
                existed = task_by_file_id.get(task_file_id)
                if not existed:
                    task_by_file_id[task_file_id] = task
                    continue
                # 同一 file_id 多条记录时，优先 updated_at 更新的任务
                current_updated = task.get("updated_at") or ""
                existed_updated = existed.get("updated_at") or ""
                if current_updated > existed_updated:
                    task_by_file_id[task_file_id] = task

        for file_id, file_record in file_by_id.items():
            task = task_by_file_id.get(file_id)
            if not task:
                continue

            all_tasks.append(
                {
                    "id": task.get("id"),
                    "project_id": str(project.id),
                    "project_name": task.get("project_name") or project.name,
                    "status": task.get("status") or file_record.status or "pending",
                    "created_at": (
                        task.get("created_at")
                        or (file_record.created_at.isoformat() if file_record.created_at else datetime.utcnow().isoformat())
                    ),
                    "annotations_count": int(task.get("annotations_count") or 0),
                }
            )

    return {"tasks": all_tasks, "total": len(all_tasks)}


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
    if len(payload.recipient_ids) == 1:
        payload.share_mode = "single"
    if payload.share_mode == "collaborative" and len(payload.recipient_ids) < 3:
        raise HTTPException(status_code=400, detail="协作标注模式下至少需要 3 位标注成员")
    if payload.share_mode == "collaborative":
        if not payload.reviewer_id:
            raise HTTPException(status_code=400, detail="协作标注模式下必须选择审核人")
    if payload.reviewer_id:
        reviewer_membership = membership_map.get(payload.reviewer_id)
        if reviewer_membership is not None:
            raise HTTPException(status_code=400, detail="审核人不能与标注成员重复")
        reviewer_belongs_to_org = (
            db.query(UserOrganization)
            .filter(
                UserOrganization.organization_id == organization.id,
                UserOrganization.user_id == payload.reviewer_id,
            )
            .first()
        )
        if not reviewer_belongs_to_org:
            raise HTTPException(status_code=400, detail="审核人必须属于当前组织")

    existing_copies = (
        db.query(Project)
        .filter(Project.source_project_id == project.id, Project.owner_id.in_([m.user.username for m in memberships]))
        .all()
    )
    existing_by_owner = {item.owner_id: item for item in existing_copies}
    membership_user_ids = [membership.user_id for membership in memberships]
    assignment_map = _build_assignment_map(project.files, membership_user_ids, payload.share_mode)

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
            existing_copy.share_mode = payload.share_mode
            existing_copy.reviewer_id = payload.reviewer_id
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
                share_mode=payload.share_mode,
                reviewer_id=payload.reviewer_id,
            )
            db.add(copied_project)
            db.flush()

        assigned_file_ids = assignment_map.get(membership.user_id, set())
        for source_file in project.files:
            db.add(
                ProjectFile(
                    project_id=copied_project.id,
                    filename=source_file.filename,
                    storage_path=source_file.storage_path,
                    mime_type=source_file.mime_type,
                    size_bytes=source_file.size_bytes,
                    uploaded_by=user.username,
                    status=source_file.status if source_file.id in assigned_file_ids else "archived",
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


@router.post("/{project_id}/reject-share")
def reject_shared_project(
    project_id: uuid.UUID,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not project.is_shared_copy:
        raise HTTPException(status_code=400, detail="当前项目不是分享副本")
    if project.owner_id != user.username:
        raise HTTPException(status_code=403, detail="仅项目接收者可以拒绝分享")
    if project.share_accepted_at:
        raise HTTPException(status_code=400, detail="项目已接收，不能拒绝")

    db.delete(project)
    db.commit()
    return {"message": "已拒绝该分享项目"}


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

    disposition_type = "inline" if (file_record.mime_type or "").startswith("image/") else "attachment"
    return Response(
        content=content,
        media_type=file_record.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": _build_content_disposition(file_record.filename, disposition_type)
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