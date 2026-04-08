from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from unicodedata import normalize
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import MetaData, Table, delete, func, inspect, or_, select
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


def _serialize_file(file_record: ProjectFile, request: Request, override_status: str | None = None) -> FileOut:
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
        "status": override_status or file_record.status,
    }
    return FileOut(**payload)


def _load_reviewed_file_ids(project_id: uuid.UUID, file_ids: list[str]) -> set[str]:
    if supabase is None or not file_ids:
        return set()

    reviewed_file_ids: set[str] = set()
    chunk_size = 200
    for idx in range(0, len(file_ids), chunk_size):
        batch_ids = file_ids[idx : idx + chunk_size]
        result = (
            supabase.table("tasks")
            .select("file_id,status,updated_at")
            .eq("project_id", str(project_id))
            .in_("file_id", batch_ids)
            .eq("status", "reviewed")
            .order("updated_at", desc=True)
            .execute()
        )
        for item in result.data or []:
            file_id = item.get("file_id")
            if file_id:
                reviewed_file_ids.add(file_id)
    return reviewed_file_ids


def _ensure_storage_client():
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase Storage 未配置，无法上传项目文件")
    return supabase.storage.from_(SUPABASE_PROJECT_FILES_BUCKET)


def _remove_storage_keys_safely(storage_keys: list[str]) -> None:
    """
    在后台执行远端文件清理，避免阻塞接口响应。
    """
    if not storage_keys or supabase is None:
        return
    try:
        bucket = _ensure_storage_client()
        bucket.remove(storage_keys)
    except Exception:
        # 后台任务失败不影响主流程，可后续接入日志系统
        pass


def _cleanup_project_task_records(
    db: Session,
    project_id: uuid.UUID,
    file_ids: list[uuid.UUID],
) -> dict[str, int]:
    """
    删除项目前清理任务侧数据，避免 tasks.file_id -> project_files.id 外键阻塞。
    兼容不同环境中表是否存在的差异（例如部分表可能尚未建表）。
    """
    bind = db.get_bind()
    table_names = set(inspect(bind).get_table_names())
    if "tasks" not in table_names:
        return {"tasks": 0, "drafts": 0, "annotations": 0, "reviews": 0}

    metadata = MetaData()
    tasks_table = Table("tasks", metadata, autoload_with=bind)

    task_filters = []
    if "project_id" in tasks_table.c:
        task_filters.append(tasks_table.c.project_id == str(project_id))
    if file_ids and "file_id" in tasks_table.c:
        task_filters.append(tasks_table.c.file_id.in_(file_ids))
    if not task_filters:
        return {"tasks": 0, "drafts": 0, "annotations": 0, "reviews": 0}

    task_scope = or_(*task_filters) if len(task_filters) > 1 else task_filters[0]
    task_ids_subquery = select(tasks_table.c.id).where(task_scope) if "id" in tasks_table.c else None
    cleanup_result = {"tasks": 0, "drafts": 0, "annotations": 0, "reviews": 0}

    if task_ids_subquery is not None:
        for table_name in ("drafts", "annotations", "reviews"):
            if table_name not in table_names:
                continue
            child_table = Table(table_name, metadata, autoload_with=bind)
            if "task_id" not in child_table.c:
                continue
            delete_result = db.execute(delete(child_table).where(child_table.c.task_id.in_(task_ids_subquery)))
            cleanup_result[table_name] = int(delete_result.rowcount or 0)

    task_delete_result = db.execute(delete(tasks_table).where(task_scope))
    cleanup_result["tasks"] = int(task_delete_result.rowcount or 0)
    return cleanup_result


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


def _serialize_project(project: Project, shared_copy_count: int = 0) -> ProjectOut:
    payload = ProjectOut.model_validate(project)
    return payload.model_copy(
        update={
            "has_shared_copies": shared_copy_count > 0,
            "shared_copy_count": max(0, int(shared_copy_count)),
        }
    )


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
    projects = query.all()
    if not projects:
        return []

    project_ids = [project.id for project in projects]
    shared_copy_rows = (
        db.query(Project.source_project_id, func.count(Project.id))
        .filter(Project.source_project_id.in_(project_ids))
        .group_by(Project.source_project_id)
        .all()
    )
    shared_copy_count_map = {
        source_project_id: int(count or 0)
        for source_project_id, count in shared_copy_rows
        if source_project_id is not None
    }

    return [
        _serialize_project(project, shared_copy_count=shared_copy_count_map.get(project.id, 0))
        for project in projects
    ]


@router.get("/task-center/overview")
def get_task_center_overview(owner_id: str, db: Session = Depends(get_db)):
    """
    任务数据中心聚合接口：
    - 以“图像(project_files)”为基础聚合该用户全部项目数据
    - 统计待标注/标注中/已标注/已审核
    - 提供项目创建与项目完成趋势所需数据
    """
    projects = (
        db.query(Project)
        .filter(Project.owner_id == owner_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    if not projects:
        return {
            "tasks": [],
            "total": 0,
            "summary": {
                "total_images": 0,
                "pending_images": 0,
                "labeling_images": 0,
                "completed_images": 0,
                "reviewed_images": 0,
            },
            "project_stats": [],
        }
    if supabase is None:
        return {
            "tasks": [],
            "total": 0,
            "summary": {
                "total_images": 0,
                "pending_images": 0,
                "labeling_images": 0,
                "completed_images": 0,
                "reviewed_images": 0,
            },
            "project_stats": [],
        }

    project_id_list = [str(project.id) for project in projects]
    project_id_set = set(project_id_list)
    current_user = db.query(User).filter(User.username == owner_id).first()
    current_user_id = current_user.id if current_user else None
    review_project_id_set = {
        str(project.id)
        for project in projects
        if project.is_shared_copy and current_user_id and project.reviewer_id == current_user_id
    }
    project_name_map = {str(project.id): project.name for project in projects}
    project_created_map = {
        str(project.id): (
            project.created_at.isoformat() if project.created_at else datetime.utcnow().isoformat()
        )
        for project in projects
    }

    all_files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id.in_([project.id for project in projects]))
        .all()
    )
    file_id_set = {str(file_record.id) for file_record in all_files}
    file_rows_by_id = {str(file_record.id): file_record for file_record in all_files}

    task_rows_by_file: dict[str, list[dict]] = {}
    project_latest_task_ts: dict[str, str] = {}

    def _ingest_task_rows(rows: list[dict]) -> None:
        for task in rows:
            file_id = str(task.get("file_id") or "")
            project_id = str(task.get("project_id") or "")
            if file_id and file_id in file_id_set:
                task_rows_by_file.setdefault(file_id, []).append(task)
            if project_id in project_id_set:
                ts = task.get("updated_at") or task.get("created_at") or ""
                if ts and ts > (project_latest_task_ts.get(project_id) or ""):
                    project_latest_task_ts[project_id] = ts

    # 主路径：按 project_id 批量查询任务
    project_chunk_size = 100
    for idx in range(0, len(project_id_list), project_chunk_size):
        batch_project_ids = project_id_list[idx : idx + project_chunk_size]
        result = (
            supabase.table("tasks")
            .select("*")
            .in_("project_id", batch_project_ids)
            .execute()
        )
        _ingest_task_rows(result.data or [])

    # 兜底：按 file_id 查询，补齐历史数据（project_id 缺失）
    file_ids = list(file_id_set)
    file_chunk_size = 200
    for idx in range(0, len(file_ids), file_chunk_size):
        batch_file_ids = file_ids[idx : idx + file_chunk_size]
        result = (
            supabase.table("tasks")
            .select("*")
            .in_("file_id", batch_file_ids)
            .execute()
        )
        _ingest_task_rows(result.data or [])

    def _latest_task(rows: list[dict]) -> dict | None:
        if not rows:
            return None
        return max(rows, key=lambda item: (item.get("updated_at") or item.get("created_at") or ""))

    all_tasks: list[dict] = []
    project_status_counter: dict[str, dict[str, int]] = {
        project_id: {"pending": 0, "labeling": 0, "done": 0, "reviewed": 0}
        for project_id in project_id_set
    }
    project_completion_ts: dict[str, str] = {}

    for file_id, file_record in file_rows_by_id.items():
        project_id = str(file_record.project_id)
        task_rows = task_rows_by_file.get(file_id, [])
        latest_task = _latest_task(task_rows)

        base_status = (file_record.status or "pending").lower()
        if base_status == "annotating":
            base_status = "labeling"
        if base_status == "completed":
            base_status = "done"

        latest_task_status = str((latest_task or {}).get("status") or "").lower()
        if latest_task_status == "annotating":
            latest_task_status = "labeling"
        if latest_task_status == "completed":
            latest_task_status = "done"

        is_reviewer_project = project_id in review_project_id_set
        final_status = "reviewed" if is_reviewer_project and latest_task_status == "reviewed" else base_status
        if final_status not in {"pending", "labeling", "done", "reviewed"}:
            # 例如 archived 不计入任务中心统计
            continue

        project_status_counter[project_id][final_status] += 1

        task_ts = (latest_task or {}).get("updated_at") or (latest_task or {}).get("created_at") or ""
        if final_status in {"done", "reviewed"} and task_ts:
            if task_ts > (project_completion_ts.get(project_id) or ""):
                project_completion_ts[project_id] = task_ts

        all_tasks.append(
            {
                "id": (latest_task or {}).get("id") or file_id,
                "task_id": (latest_task or {}).get("id"),
                "file_id": file_id,
                "project_id": project_id,
                "project_name": project_name_map.get(project_id) or "未分类项目",
                "status": final_status,
                "created_at": (
                    (file_record.created_at.isoformat() if file_record.created_at else None)
                    or (latest_task or {}).get("created_at")
                    or datetime.utcnow().isoformat()
                ),
                "annotations_count": int((latest_task or {}).get("annotations_count") or 0),
            }
        )

    pending_images = sum(item["pending"] for item in project_status_counter.values())
    labeling_images = sum(item["labeling"] for item in project_status_counter.values())
    completed_images = sum(item["done"] for item in project_status_counter.values())
    reviewed_images = sum(item["reviewed"] for item in project_status_counter.values())
    total_images = pending_images + labeling_images + completed_images

    project_stats: list[dict] = []
    for project_id in project_id_set:
        status_counter = project_status_counter[project_id]
        is_completed = (
            status_counter["pending"] == 0
            and status_counter["labeling"] == 0
            and (status_counter["done"] + status_counter["reviewed"]) > 0
        )
        completed_at = None
        if is_completed:
            completed_at = project_completion_ts.get(project_id) or project_latest_task_ts.get(project_id)

        project_stats.append(
            {
                "project_id": project_id,
                "project_name": project_name_map.get(project_id) or "未分类项目",
                "created_at": project_created_map.get(project_id) or datetime.utcnow().isoformat(),
                "is_completed": is_completed,
                "completed_at": completed_at,
            }
        )

    all_tasks.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    project_stats.sort(key=lambda item: item.get("created_at") or "", reverse=True)

    return {
        "tasks": all_tasks,
        "total": len(all_tasks),
        "summary": {
            "total_images": total_images,
            "pending_images": pending_images,
            "labeling_images": labeling_images,
            "completed_images": completed_images,
            "reviewed_images": reviewed_images,
        },
        "project_stats": project_stats,
    }


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
    reviewer_user: User | None = None
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
        reviewer_user = db.query(User).filter(User.id == payload.reviewer_id).first()
        if not reviewer_user:
            raise HTTPException(status_code=404, detail="审核人不存在")

    target_owners = [membership.user.username for membership in memberships]
    if reviewer_user and reviewer_user.username not in target_owners:
        target_owners.append(reviewer_user.username)
    existing_copies = (
        db.query(Project)
        .filter(Project.source_project_id == project.id, Project.owner_id.in_(target_owners))
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
            existing_file_ids = [file_record.id for file_record in existing_copy.files]
            _cleanup_project_task_records(db, existing_copy.id, existing_file_ids)
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

    if reviewer_user and reviewer_user.username not in [membership.user.username for membership in memberships]:
        copied_name = f"[审核] {project.name} - {reviewer_user.username}"
        existing_copy = existing_by_owner.get(reviewer_user.username)
        if existing_copy:
            existing_copy.name = copied_name
            existing_copy.description = project.description
            existing_copy.share_message = payload.message
            existing_copy.shared_by = user.username
            existing_copy.shared_at = datetime.utcnow()
            existing_copy.organization_nickname = payload.organization_nickname
            existing_copy.share_accepted_at = None
            existing_copy.share_mode = payload.share_mode
            existing_copy.reviewer_id = payload.reviewer_id
            reviewer_project = existing_copy
            existing_file_ids = [file_record.id for file_record in existing_copy.files]
            _cleanup_project_task_records(db, existing_copy.id, existing_file_ids)
            db.query(ProjectFile).filter(ProjectFile.project_id == existing_copy.id).delete()
        else:
            reviewer_project = Project(
                name=copied_name,
                description=project.description,
                owner_id=reviewer_user.username,
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
            db.add(reviewer_project)
            db.flush()

        for source_file in project.files:
            db.add(
                ProjectFile(
                    project_id=reviewer_project.id,
                    filename=source_file.filename,
                    storage_path=source_file.storage_path,
                    mime_type=source_file.mime_type,
                    size_bytes=source_file.size_bytes,
                    uploaded_by=user.username,
                    status="archived",
                )
            )

        copied_to.append(
            {"user_id": reviewer_user.id, "username": reviewer_user.username, "project_id": reviewer_project.id}
        )

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

    file_ids = [file_record.id for file_record in project.files]
    try:
        _cleanup_project_task_records(db, project.id, file_ids)
        db.delete(project)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"拒绝分享并删除项目失败: {exc}") from exc

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
def list_project_files(
    project_id: uuid.UUID,
    request: Request,
    sync_review_status: bool = Query(default=False, description="是否同步 tasks 中的 reviewed 状态（会更慢）"),
    db: Session = Depends(get_db),
):
    file_records = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.created_at.desc())
        .all()
    )
    reviewed_file_ids: set[str] = set()
    if sync_review_status:
        reviewed_file_ids = _load_reviewed_file_ids(project_id, [str(file_record.id) for file_record in file_records])
    return [
        _serialize_file(
            file_record,
            request,
            override_status="reviewed" if str(file_record.id) in reviewed_file_ids else None,
        )
        for file_record in file_records
    ]


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
def delete_project(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_current_user(db, authorization)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.owner_id != user.username:
        raise HTTPException(status_code=403, detail="仅项目拥有者可以删除项目")

    if not project.is_shared_copy:
        shared_copy_count = (
            db.query(Project)
            .filter(Project.source_project_id == project.id)
            .count()
        )
        if shared_copy_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"项目已分享给 {shared_copy_count} 位成员，请先让接收方删除分享副本后再删除源项目",
            )

    file_ids = [file_record.id for file_record in project.files]
    storage_keys = [file_record.storage_path for file_record in project.files if file_record.storage_path]
    should_cleanup_storage = False
    if storage_keys and not project.is_shared_copy:
        other_file_count = (
            db.query(ProjectFile)
            .filter(ProjectFile.storage_path.in_(storage_keys), ProjectFile.project_id != project.id)
            .count()
        )
        should_cleanup_storage = other_file_count == 0

    cleanup_result = {"tasks": 0, "drafts": 0, "annotations": 0, "reviews": 0}
    try:
        cleanup_result = _cleanup_project_task_records(db, project.id, file_ids)
        db.delete(project)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除项目失败: {exc}") from exc

    cleanup_scheduled = False
    warning: str | None = None
    if should_cleanup_storage:
        if supabase is None:
            warning = "Supabase Storage 未配置，已跳过远端文件清理"
        else:
            background_tasks.add_task(_remove_storage_keys_safely, storage_keys)
            cleanup_scheduled = True

    response = {
        "success": True,
        "message": "项目已删除",
        "cleanup": cleanup_result,
        "storage_cleanup_scheduled": cleanup_scheduled,
    }
    if warning:
        response["warning"] = warning
    return response
