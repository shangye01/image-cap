// src/api/projectStorage.ts
import request from './request'

export interface BackendProject {
  id: string
  name: string
  description: string | null
  owner_id: string
  created_at: string
  source_project_id?: string | null
  is_shared_copy?: boolean
  shared_by?: string | null
  shared_at?: string | null
  share_message?: string | null
  organization_nickname?: string | null
  share_accepted_at?: string | null
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
  task_id: string        // ✅ 现在是 "项目名_001" 格式
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

export const createProject = (payload: {
  name: string
  description?: string
  owner_id: string
  organization_nickname?: string
}) =>
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

export const shareProject = (
  projectId: string,
  payload: { recipient_ids: string[]; organization_nickname: string; message?: string },
) => request.post<{ message: string; copied_to: Array<{ user_id: string; username: string; project_id: string }> }>(`/projects/${projectId}/share`, payload)

export const acceptSharedProject = (projectId: string) =>
  request.post<{ message: string; accepted_at?: string | null }>(`/projects/${projectId}/accept-share`)

// ✅ 路径已更改为 /sessions，与后端严格对齐
export const createAnnotationSession = (
  projectId: string,
  payload: { file_ids: string[]; use_keywords: boolean; keywords: string[] }
) => request.post<AnnotationSessionResponse>(
  `/projects/${projectId}/sessions`, 
  payload,
  { timeout: 120000 } // 增加到 2 分钟，因为包含 AI 预测
)

// ❌ 旧的 getAnnotationSessionTask 已彻底删除！

// src/api/projectStorage.ts - 在文件末尾添加

// 获取文件夹中的任务列表（用于标注中文件夹的继续标注功能）
export const getFolderTasks = (projectId: string, folderName: 'pending' | 'labeling' | 'done') => {
  const statusMap = {
    'pending': 'pending',
    'labeling': 'labeling', 
    'done': 'done'
  }
  const status = statusMap[folderName]
  
  console.log(`[API] 获取文件夹任务 | projectId=${projectId}, folder=${folderName}, status=${status}`)
  
  return request.get(`/projects/${projectId}/folder-tasks`, {
    params: { status }
  })
}



// 获取单个文件对应的任务
export const getTaskByFileId = (projectId: string, fileId: string) => {
  return request.get(`/projects/${projectId}/file-task`, {
    params: { file_id: fileId }
  })
}

// 获取相邻任务（上一个/下一个）
export const getAdjacentTask = (
  projectId: string,
  currentTaskId: string,
  direction: 'next' | 'prev'
) => {
  return request.get(`/projects/${projectId}/tasks/${currentTaskId}/adjacent`, {
    params: { direction }
  })
}

// 获取任务详情（如果还没有的话）
export const getTaskById = (taskId: string) => {
  return request.get(`/tasks/${taskId}`)
}