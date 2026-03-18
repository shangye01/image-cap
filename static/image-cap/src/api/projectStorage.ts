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
  mime_type: string
  size_bytes: number
  uploaded_by: string
  created_at: string
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

export const createAnnotationSession = (
  projectId: string,
  payload: { file_ids: string[]; use_keywords: boolean; keywords: string[] }
) => request.post<AnnotationSessionResponse>(`/projects/${projectId}/annotation-session`, payload)

export const getAnnotationSessionTask = (projectId: string, taskId: string) =>
  request.get<{ success: boolean; task: AnnotationSessionTask }>(
    `/projects/${projectId}/annotation-session/${taskId}`
  )