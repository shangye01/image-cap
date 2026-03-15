// annotation.ts 修复
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { supabase } from '@/supabase'

// ========== 类型定义保持不变 ==========

export interface Annotation {
  id?: string
  x: number
  y: number
  width: number
  height: number
  label: string
  confidence?: number
  isCandidate?: boolean
  [key: string]: any
}

export interface TaskInfo {
  id?: string
  projectId?: string
  imageUrl?: string
  imageStoragePath?: string
  yoloVersion?: string
  [key: string]: any
}

export interface UserData {
  id: string
  token?: string
  [key: string]: any
}

export type TaskStatus = 'idle' | 'loading' | 'annotating' | 'submitting'

// ========== Store 定义 ==========

export const useAnnotationStore = defineStore('annotation', () => {
  // ============= 状态 =============
  const annotations = ref<Annotation[]>([])
  const selectedId = ref<string | null>(null)
  
  // 任务相关
  const currentTaskId = ref<string | null>(null)
  const currentProjectId = ref<string | null>(null)
  const taskStatus = ref<TaskStatus>('idle')
  const taskInfo = ref<TaskInfo>({})
  
  // 用户相关
  const userId = ref<string>(localStorage.getItem('userId') || '')
  const authToken = ref<string>(localStorage.getItem('authToken') || '')
  
  // ============= 私有辅助方法 =============
  
  const generateId = (prefix = 'ann') => `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  // ✅ 修复：使用 ReturnType 代替 NodeJS.Timeout
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
  
  const debouncedAutoSave = () => {
    if (!currentTaskId.value) return
    
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(async () => {
      await saveDraft()
    }, 2000)
  }
  
  // ============= 核心持久化方法 =============
  
  const loadTask = async (taskId: string): Promise<void> => {
    taskStatus.value = 'loading'
    
    try {
      const { data: task, error: taskError } = await supabase
        .from('tasks')
        .select('*')
        .eq('id', taskId)
        .single()
      
      if (taskError) throw taskError
      
      const { data: draft, error: draftError } = await supabase
        .from('drafts')
        .select('annotations_json')
        .eq('task_id', taskId)
        .single()
      
      let loadedAnnotations: Annotation[] = []
      if (draft?.annotations_json) {
        loadedAnnotations = draft.annotations_json
      } else {
        const { data: anns, error: annError } = await supabase
          .from('annotations')
          .select('*')
          .eq('task_id', taskId)
        
        if (annError) throw annError
        loadedAnnotations = anns || []
      }
      
      annotations.value = loadedAnnotations.map(ann => ({
        ...ann,
        id: ann.id || generateId('ann')
      }))
      
      currentTaskId.value = taskId
      currentProjectId.value = task.project_id || null
      taskInfo.value = {
        id: task.id,
        projectId: task.project_id,
        imageUrl: task.image_url,
        imageStoragePath: task.image_storage_path,
        yoloVersion: task.yolo_version
      }
      
      taskStatus.value = 'annotating'
      
    } catch (error) {
      console.error('❌ 加载任务失败:', error)
      taskStatus.value = 'idle'
      throw error
    }
  }
  
  const saveDraft = async (): Promise<void> => {
    if (!currentTaskId.value || annotations.value.length === 0) return
    
    try {
      const { error } = await supabase
        .from('drafts')
        .upsert({
          task_id: currentTaskId.value,
          user_id: userId.value || 'anonymous',
          annotations_json: annotations.value,
          saved_at: new Date().toISOString()
        })
      
      if (error) throw error
      console.log('✅ 草稿已自动保存')
    } catch (error) {
      console.error('❌ 保存草稿失败:', error)
    }
  }
  
  const submitAnnotations = async (): Promise<void> => {
    if (!currentTaskId.value || annotations.value.length === 0) {
      throw new Error('没有可提交的数据')
    }
    
    taskStatus.value = 'submitting'
    
    try {
      await supabase
        .from('drafts')
        .delete()
        .eq('task_id', currentTaskId.value)
      
      const annsToInsert = annotations.value.map(ann => ({
        id: ann.id || generateId('ann'),
        task_id: currentTaskId.value,
        label: ann.label,
        x: ann.x,
        y: ann.y,
        width: ann.width,
        height: ann.height,
        confidence: ann.confidence || 1.0,
        annotated_by: userId.value,
        is_verified: false
      }))
      
      const { error: insertError } = await supabase
        .from('annotations')
        .insert(annsToInsert)
      
      if (insertError) throw insertError
      
      const { error: updateError } = await supabase
        .from('tasks')
        .update({
          status: 'completed',
          annotations_count: annotations.value.length,
          completed_at: new Date().toISOString()
        })
        .eq('id', currentTaskId.value)
      
      if (updateError) throw updateError
      
      await checkTrainingTrigger()
      
      taskStatus.value = 'idle'
      
    } catch (error) {
      console.error('❌ 提交失败:', error)
      taskStatus.value = 'annotating'
      throw error
    }
  }
  
  // ✅ 修复：正确处理 Supabase RPC 返回类型
  const checkTrainingTrigger = async (): Promise<void> => {
    try {
      const { data, error } = await supabase
        .rpc('get_training_ready_count')
      
      if (error) throw error
      
      // 类型断言为数组
      const result = data as unknown as { count: number }[] | null
      const readyCount = result?.[0]?.count || 0
      
      if (readyCount >= 1000) {
        console.log(`🚀 触发模型训练，可用数据: ${readyCount}条`)
        await fetch('/api/train', { method: 'POST' })
      }
    } catch (error) {
      console.error('检查训练条件失败:', error)
    }
  }
  
  // ============= 原有接口（保持兼容） =============
  
  const addAnnotation = (ann: Annotation): void => {
    const id = ann.id || generateId()
    annotations.value.push({
      ...ann,
      id,
      color: undefined // 明确移除color
    })
    debouncedAutoSave()
  }
  
  const deleteAnnotation = (id: string): void => {
    annotations.value = annotations.value.filter(ann => ann.id !== id)
    if (selectedId.value === id) {
      selectedId.value = null
    }
    debouncedAutoSave()
  }
  
// stores/annotation.ts 中的 updateAnnotation
const updateAnnotation = (id: string, updates: Partial<Annotation>): void => {
  const index = annotations.value.findIndex(ann => ann.id === id)
  if (index !== -1) {
    // 清理更新数据，移除 color（颜色应该从 labelColorMap 获取）
    const cleanUpdates = { ...updates }
    delete cleanUpdates.color
    
    // 确保数值是数字类型
    if (cleanUpdates.x !== undefined) cleanUpdates.x = Number(cleanUpdates.x)
    if (cleanUpdates.y !== undefined) cleanUpdates.y = Number(cleanUpdates.y)
    if (cleanUpdates.width !== undefined) cleanUpdates.width = Number(cleanUpdates.width)
    if (cleanUpdates.height !== undefined) cleanUpdates.height = Number(cleanUpdates.height)
    
    annotations.value[index] = {
      ...annotations.value[index],
      ...cleanUpdates
    } as Annotation
    
    console.log('✅ 更新标注:', id, cleanUpdates)
    debouncedAutoSave()
  }
}
  
  const clearAnnotations = (): void => {
    annotations.value = []
    selectedId.value = null
  }
  
  const setAnnotations = (anns: Annotation[]): void => {
    annotations.value = anns.map(ann => {
      const cleanAnn = { ...ann }
      delete cleanAnn.color
      return {
        ...cleanAnn,
        id: ann.id || generateId('pred')
      }
    })
    debouncedAutoSave()
  }
  
  const setCurrentTask = (task: TaskInfo): void => {
    currentTaskId.value = task.id || null
    currentProjectId.value = task.projectId || null
    taskInfo.value = task
    taskStatus.value = 'annotating'
  }
  
  const clearCurrentTask = (): void => {
    currentTaskId.value = null
    currentProjectId.value = null
    taskInfo.value = {}
    taskStatus.value = 'idle'
    clearAnnotations()
  }
  
  const setUser = (userData: UserData): void => {
    userId.value = userData.id
    authToken.value = userData.token || ''
    localStorage.setItem('userId', userData.id)
    localStorage.setItem('authToken', userData.token || '')
  }
  
  const logout = (): void => {
    userId.value = ''
    authToken.value = ''
    localStorage.removeItem('userId')
    localStorage.removeItem('authToken')
    clearCurrentTask()
  }
  
  // ============= 监听自动保存 =============
  
  watch(annotations, () => {
    debouncedAutoSave()
  }, { deep: true })
  
  // ============= 返回值 =============
  
  return {
    // 状态
    annotations,
    selectedId,
    currentTaskId,
    currentProjectId,
    taskStatus,
    taskInfo,
    userId,
    authToken,
    
    // 原有方法
    addAnnotation,
    deleteAnnotation,
    updateAnnotation,
    clearAnnotations,
    setAnnotations,
    setCurrentTask,
    clearCurrentTask,
    setUser,
    logout,
    
    // 新增持久化方法
    loadTask,
    saveDraft,
    submitAnnotations,
    checkTrainingTrigger
  }
})