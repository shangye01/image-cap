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


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: str
    created_at: datetime

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

    class Config:
        from_attributes = True