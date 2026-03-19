// src/api/projectStorage.ts
import request from './request'

export interface BackendProject {
  id: string
  name: string
  description: string | null
  owner_id: string
  created_at: string
}

export interface BackendProjectFile {
  id: string
  project_id: string
  filename: string
  storage_path: string
  storage_backend?: 'supabase'
  mime_type: string
  size_bytes: number
  uploaded_by: string
  created_at: string
  download_url?: string | null
  preview_url?: string | null
}

export interface AnnotationSessionTask {
  task_id: string
  file_id: string
  filename: string
  storage_path: string
  image_url: string
  project_id: string
  project_name: string
  use_keywords: boolean
  keywords: string[]
  status: string
  annotations?: any[] // ✅ 接收后端返回的预标注框
}

export interface AnnotationSessionResponse {
  success: boolean
  project_id: string
  project_name: string
  use_keywords: boolean
  keywords: string[]
  tasks: AnnotationSessionTask[]
  first_task: AnnotationSessionTask
}

export const createProject = (payload: { name: string; description?: string; owner_id: string }) =>
  request.post<BackendProject>('/projects', payload)

export const listProjects = (ownerId?: string) =>
  request.get<BackendProject[]>('/projects', {
    params: ownerId ? { owner_id: ownerId } : undefined,
  })

export const uploadProjectFile = (projectId: string, file: File, uploadedBy: string) => {
  const formData = new FormData()
  formData.append('uploaded_by', uploadedBy)
  formData.append('file', file)
  return request.post<BackendProjectFile>(`/projects/${projectId}/files`, formData)
}

export const listProjectFiles = (projectId: string) =>
  request.get<BackendProjectFile[]>(`/projects/${projectId}/files`)

export const getProjectFileDownloadUrl = (fileId: string) => `/api/projects/files/${fileId}/download`

export const deleteProjectApi = (projectId: string) =>
  request.delete(`/projects/${projectId}`)

// ✅ 路径已更改为 /sessions，与后端严格对齐
export const createAnnotationSession = (
  projectId: string,
  payload: { file_ids: string[]; use_keywords: boolean; keywords: string[] }
) => request.post<AnnotationSessionResponse>(`/projects/${projectId}/sessions`, payload)

// ❌ 旧的 getAnnotationSessionTask 已彻底删除！