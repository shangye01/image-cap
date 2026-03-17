from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    mime_type: str
    size_bytes: int
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True