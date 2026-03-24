from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import List, Optional


class AnnotationSessionCreate(BaseModel):
    file_ids: List[str]
    use_keywords: bool
    keywords: Optional[List[str]] = []


class AnnotationSessionTask(BaseModel):
    task_id: str
    file_id: str
    filename: str
    storage_path: str
    image_url: str
    project_id: str
    project_name: str
    use_keywords: bool
    keywords: List[str]
    status: str
    annotations: Optional[List[dict]] = []


class AnnotationSessionResponse(BaseModel):
    success: bool
    project_id: str
    project_name: str
    use_keywords: bool
    keywords: List[str]
    tasks: List[AnnotationSessionTask]
    first_task: AnnotationSessionTask


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    owner_id: str = Field(min_length=1, max_length=64)
    organization_nickname: str | None = Field(default=None, max_length=100)


class ProjectShareCreate(BaseModel):
    recipient_ids: List[str] = Field(min_length=1)
    organization_nickname: str = Field(min_length=1, max_length=100)
    message: str | None = Field(default=None, max_length=500)


class SharedProjectMeta(BaseModel):
    is_shared_copy: bool = False
    source_project_id: UUID | None = None
    shared_by: str | None = None
    shared_at: datetime | None = None
    share_message: str | None = None
    organization_nickname: str | None = None
    share_accepted_at: datetime | None = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: str
    created_at: datetime
    source_project_id: UUID | None = None
    is_shared_copy: bool = False
    shared_by: str | None = None
    shared_at: datetime | None = None
    share_message: str | None = None
    organization_nickname: str | None = None
    share_accepted_at: datetime | None = None

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    storage_path: str
    storage_backend: str = "supabase"
    mime_type: str
    size_bytes: int
    uploaded_by: str
    created_at: datetime
    download_url: str | None = None
    preview_url: str | None = None
    status: str = "pending"

    class Config:
        from_attributes = True