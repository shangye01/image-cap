// composables/useTaskFlow.js
import { ref } from 'vue'
import { supabase } from '@/supabase'
// ❌ 已经删除了对 getAnnotationSessionTask 的引入

export function useTaskFlow(store, imageObj, labelColorMap) {
  const taskLoading = ref(false)
  const submitLoading = ref(false)
  const taskError = ref('')
  const taskSuccess = ref('')

const loadTaskImage = async (task) => {
  return await new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = task.image_url || task.imageUrl

    img.onload = () => {
      imageObj.value = img
      store.setCurrentTask({
        id: task.task_id || task.id,
        projectId: task.project_id || task.projectId || null,
        projectName: task.project_name || task.projectName || '未命名项目',  // ✅ 添加项目名
        imageUrl: task.image_url || task.imageUrl,
        imageStoragePath: task.storage_path || task.image_storage_path || task.imageStoragePath,
        yoloVersion: task.yolo_version || task.yoloVersion,
      })
      resolve(img)
    }

    img.onerror = () => reject(new Error('图片加载失败'))
  })
}

  // 加载测试图片
  const loadTestImage = () => {
    taskError.value = ''
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = '/public/test.jpg'
    
    img.onload = () => {
      imageObj.value = img
      store.clearAnnotations()
      taskSuccess.value = '测试图片加载成功'
      setTimeout(() => taskSuccess.value = '', 2000)
    }
    img.onerror = () => {
      taskError.value = '测试图片加载失败'
    }
  }

  // 加载下一个任务
  const loadNextTask = async () => {
    if (taskLoading.value) return
    
    taskLoading.value = true
    taskError.value = ''
    
    try {
      const { data, error } = await supabase
        .from('tasks')
        .select('*')
        .eq('status', 'pending')
        .limit(1)
        .single()
      
      if (error || !data) {
        throw new Error('没有可用的任务')
      }

      await loadTaskImage(data)
      await loadAnnotations(data.id)
      taskLoading.value = false
      taskSuccess.value = `任务 ${data.id} 加载成功`
      
    } catch (e) {
      taskLoading.value = false
      taskError.value = '没有可用任务'
      console.error(e)
    }
  }

 const fetchProjectTask = async (projectId, taskId) => {
  if (!projectId || !taskId) return false

  taskLoading.value = true
  taskError.value = ''

  try {
    const response = await fetch(`http://localhost:8000/api/tasks/${taskId}`)
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '任务请求失败')
    }
    
    const data = await response.json()

    if (data.task) {
      // 确保 project_name 存在
      if (!data.task.project_name && data.task.project_id) {
        data.task.project_name = data.task.project_id
      }
      
      await loadTaskImage(data.task)
      
      if (data.annotations && data.annotations.length > 0) {
        data.annotations.forEach(ann => {
          if (ann.color && ann.label && !labelColorMap.has(ann.label)) {
            labelColorMap.set(ann.label, ann.color)
          }
        })
      }
      
      store.setAnnotations(data.annotations || [])
      
      taskSuccess.value = `任务 ${taskId} 加载成功`
      setTimeout(() => (taskSuccess.value = ''), 2500)
      return true
    }
    throw new Error('未找到任务数据')
  } catch (error) {
    console.error('加载项目任务失败:', error)
    taskError.value = error.message || '项目任务加载失败'
    return false
  } finally {
    taskLoading.value = false
  }
}

  // 加载标注数据（草稿优先）
  const loadAnnotations = async (taskId) => {
    if (!taskId) {
      console.warn('⚠️ loadAnnotations: taskId 为空')
      return
    }
    
    try {
      const { data: draft } = await supabase
        .from('drafts')
        .select('annotations_json')
        .eq('task_id', taskId)
        .maybeSingle() 
      
      if (draft?.annotations_json) {
        store.annotations = draft.annotations_json
      }
    } catch (e) {
      console.error('加载草稿失败:', e)
    }
  }
const submitAnnotations = async () => {
  if (!store.currentTaskId) {
    taskError.value = '没有正在进行的任务'
    return false
  }
  
  if (store.annotations.length === 0) {
    taskError.value = '请先完成标注'
    return false
  }
  
  submitLoading.value = true
  
  try {
    const response = await fetch(`http://localhost:8000/api/annotations/${store.currentTaskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        annotations: store.annotations,
        is_draft: false,
        user_id: store.userId || 'anonymous'
      })
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || '提交失败')
    }
    
    taskSuccess.value = '✅ 提交成功！'
    setTimeout(() => {
      taskSuccess.value = ''
    }, 2000)
    
    return true
    
  } catch (e) {
    taskError.value = `提交失败: ${e.message}`
    console.error('提交标注失败:', e)
    return false
  } finally {
    submitLoading.value = false
  }
}
 // 修改原有的保存草稿方法
const saveDraftHandler = async () => {
  if (!store.currentTaskId || store.annotations.length === 0) return
  
  const draftData = {
    file_id: store.currentFileId,
    task_id: store.currentTaskId,
    project_id: currentProject.value?.id,
    annotations: store.annotations,
    saved_at: new Date().toISOString()
  }
  
  // 1. 保存到 localStorage（页面级）
  const draftKey = `annotation_draft_${currentProject.value?.id}_${store.currentFileId}`
  localStorage.setItem(draftKey, JSON.stringify(draftData))
  
  // 2. 保存到 sessionStorage（会话级）
  sessionStorage.setItem(`draft_${store.currentTaskId}`, JSON.stringify(draftData))
  
  // 3. 调用API保存到后端草稿表（如果有）
  try {
    await saveDraftAnnotation({
      file_id: store.currentFileId,
      task_id: store.currentTaskId,
      annotations: store.annotations
    })
    console.log('[DRAFT] 已保存到后端草稿表')
  } catch (e) {
    console.log('[DRAFT] 后端保存失败，仅保存到本地:', e)
  }
  
  // 显示成功提示
  alert('草稿已保存')
}

  // 放弃任务
  const abandonTask = async () => {
    if (!store.currentTaskId) return
    
    const confirmed = confirm('确定放弃任务吗？已标注的内容将丢失。')
    if (!confirmed) return
    
    try {
      await supabase
        .from('drafts')
        .delete()
        .eq('task_id', store.currentTaskId)
      
      store.clearCurrentTask()
      imageObj.value = null
      taskError.value = ''
      taskSuccess.value = ''
    } catch (e) {
      console.error('放弃任务失败:', e)
    }
  }

  // 恢复任务
  const restoreTask = async (taskId) => {
    try {
      console.log('🔄 开始恢复任务:', taskId)
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.task) {
        await loadTaskImage({
          ...data.task,
          imageUrl: data.task.image_url,
          imageStoragePath: data.task.image_storage_path
        })
        
        if (data.annotations && data.annotations.length > 0) {
          data.annotations.forEach(ann => {
            if (ann.color && ann.label && !labelColorMap.has(ann.label)) {
              labelColorMap.set(ann.label, ann.color)
            }
          })
        }
        
        store.setAnnotations(data.annotations || [])
        console.log('✅ 任务恢复成功:', data.task.image_url)
        return true
      }
      return false
    } catch (error) {
      console.error('❌ 恢复任务失败:', error)
      return false
    }
  }

  return {
    taskLoading,
    submitLoading,
    taskError,
    taskSuccess,
    loadNextTask,
    loadTestImage,
    submitAnnotations,
    saveDraftHandler,
    abandonTask,
    fetchProjectTask,
    restoreTask
  }
}