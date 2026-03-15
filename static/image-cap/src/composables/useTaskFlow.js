// composables/useTaskFlow.js
import { ref } from 'vue'
import { supabase } from '@/supabase'

export function useTaskFlow(store, imageObj, labelColorMap) {
  const taskLoading = ref(false)
  const submitLoading = ref(false)
  const taskError = ref('')
  const taskSuccess = ref('')
  
  // 新增：存储项目内的图片列表
  const projectImages = ref([])
  const currentIndex = ref(0)

  // --- 保留你原有的：加载测试图片 ---
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

  // --- 新增核心：根据 Project ID 加载该项目的第一张图 ---
  const fetchProjectTask = async (projectId) => {
    if (!projectId) return
    taskLoading.value = true
    taskError.value = ''
    
    try {
      // 1. 从 Supabase 获取该项目的所有 pending 任务
      const { data: tasks, error } = await supabase
        .from('tasks')
        .select('*')
        .eq('project_id', projectId)
        .order('id', { ascending: true })
      
      if (error) throw error

      if (tasks && tasks.length > 0) {
        projectImages.value = tasks
        currentIndex.value = 0
        // 2. 自动加载第一张
        await loadSpecificTask(tasks[0])
      } else {
        // 3. 兜底逻辑：如果数据库没找到，尝试从本地 localStorage 查找演示数据
        loadMockLocalData(projectId)
      }
    } catch (e) {
      console.error('获取项目任务失败:', e)
      taskError.value = '任务加载失败，尝试载入演示数据'
      loadMockLocalData(projectId)
    } finally {
      taskLoading.value = false
    }
  }

  // 内部辅助：加载特定的 Task 数据并显示图片
  const loadSpecificTask = (task) => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.src = task.image_url || task.url

      img.onload = () => {
        imageObj.value = img
        // 保持你原有的 store 赋值习惯
        store.setCurrentTask({
          id: task.id,
          projectId: task.project_id || task.projectId,
          imageUrl: task.image_url || task.url,
          imageStoragePath: task.image_storage_path,
          yoloVersion: task.yolo_version
        })
        
        // 加载你原有的标注/草稿逻辑
        loadAnnotations(task.id)
        resolve(img)
      }
      img.onerror = () => {
        taskError.value = '图片加载失败'
        reject()
      }
    })
  }

  // --- 保留你原有的：加载下一个任务 ---
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
      
      if (error || !data) throw new Error('没有可用的任务')
      await loadSpecificTask(data)
      taskSuccess.value = `任务 ${data.id} 加载成功`
    } catch (e) {
      taskError.value = '没有可用任务'
    } finally {
      taskLoading.value = false
    }
  }

  // --- 保留你原有的：加载标注数据（草稿优先） ---
  const loadAnnotations = async (taskId) => {
    if (!taskId) return
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

  // --- 保留你原有的：提交标注 ---
  const submitAnnotations = async () => {
    if (!store.currentTaskId) {
      taskError.value = '没有正在进行的任务'
      return
    }
    if (store.annotations.length === 0) {
      taskError.value = '请先完成标注'
      return
    }
    submitLoading.value = true
    try {
      const response = await fetch(`/api/annotations/${store.currentTaskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          annotations: store.annotations,
          is_draft: false,
          user_id: store.userId || 'anonymous'
        })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '提交失败')
      
      taskSuccess.value = '✅ 提交成功！'
      setTimeout(() => {
        store.clearCurrentTask()
        imageObj.value = null
        taskSuccess.value = ''
      }, 2000)
    } catch (e) {
      taskError.value = `提交失败: ${e.message}`
    } finally {
      submitLoading.value = false
    }
  }

  // --- 保留你原有的：保存草稿 ---
  const saveDraftHandler = async () => {
    if (!store.currentTaskId || store.annotations.length === 0) return
    try {
      const response = await fetch(`/api/annotations/${store.currentTaskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          annotations: store.annotations,
          is_draft: true,
          user_id: store.userId || 'anonymous'
        })
      })
      if (response.ok) {
        taskSuccess.value = '💾 草稿已保存'
        setTimeout(() => taskSuccess.value = '', 2000)
      } else {
        throw new Error('保存失败')
      }
    } catch (e) {
      taskError.value = '保存草稿失败'
    }
  }

  // --- 保留你原有的：放弃任务 ---
  const abandonTask = async () => {
    if (!store.currentTaskId) return
    const confirmed = confirm('确定放弃任务吗？已标注的内容将丢失。')
    if (!confirmed) return
    try {
      await supabase.from('drafts').delete().eq('task_id', store.currentTaskId)
      store.clearCurrentTask()
      imageObj.value = null
      taskError.value = ''
      taskSuccess.value = ''
    } catch (e) {
      console.error('放弃任务失败:', e)
    }
  }

  // --- 保留你原有的：恢复任务方法 ---
  const restoreTask = async (taskId) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data.task) {
        const taskInfo = {
          ...data.task,
          imageUrl: data.task.image_url,
          imageStoragePath: data.task.image_storage_path,
          projectId: data.task.project_id,
          yoloVersion: data.task.yolo_version
        }
        store.setCurrentTask(taskInfo)
        if (data.annotations?.length > 0) {
          data.annotations.forEach(ann => {
            if (ann.color && ann.label && !labelColorMap.has(ann.label)) {
              labelColorMap.set(ann.label, ann.color)
            }
          })
        }
        store.setAnnotations(data.annotations || [])
        return true
      }
      return false
    } catch (error) {
      console.error('❌ 恢复任务失败:', error)
      return false
    }
  }

  // 本地 Mock 兜底逻辑
  const loadMockLocalData = (projectId) => {
    const all = JSON.parse(localStorage.getItem('my_projects') || '[]')
    const target = all.find(p => p.id.toString() === projectId.toString())
    if (target) {
      const mockTask = {
        id: `mock-${projectId}-0`,
        image_url: `https://picsum.photos/1200/800?random=${projectId}`,
        project_id: projectId
      }
      loadSpecificTask(mockTask)
    }
  }

  return {
    taskLoading,
    submitLoading,
    taskError,
    taskSuccess,
    projectImages,
    currentIndex,
    fetchProjectTask, // 在标注页 onMounted 调用
    loadNextTask,
    loadTestImage,
    submitAnnotations,
    saveDraftHandler,
    abandonTask,
    restoreTask
  }
}