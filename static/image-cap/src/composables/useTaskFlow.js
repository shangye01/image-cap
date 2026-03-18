// composables/useTaskFlow.js
import { ref } from 'vue'
import { supabase } from '@/supabase'
import { getAnnotationSessionTask } from '@/api/projectStorage'

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
      // 从 Supabase 获取一个 pending 状态的任务
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
      const { data } = await getAnnotationSessionTask(projectId, taskId)
      await loadTaskImage(data.task)
      await loadAnnotations(data.task.task_id)
      taskSuccess.value = `任务 ${data.task.task_id} 加载成功`
      setTimeout(() => (taskSuccess.value = ''), 2500)
      return true
    } catch (error) {
      console.error('加载项目任务失败:', error)
      taskError.value = error?.response?.data?.detail || '项目任务加载失败'
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
        .maybeSingle()  // ✅ 使用 maybeSingle() 而不是 single()，避免 406 错误
      
      if (draft?.annotations_json) {
        store.annotations = draft.annotations_json
      }
    } catch (e) {
      console.error('加载草稿失败:', e)
      // 不抛出错误，让流程继续
    }
  }
  // 提交标注
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

  // 保存草稿
  const saveDraftHandler = async () => {
    if (!store.currentTaskId || store.annotations.length === 0) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/annotations/${store.currentTaskId}`, {
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
      console.error(e)
    }
  }

  // 放弃任务
  const abandonTask = async () => {
    if (!store.currentTaskId) return
    
    const confirmed = confirm('确定放弃任务吗？已标注的内容将丢失。')
    if (!confirmed) return
    
    try {
      // 删除草稿
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

  // ✅ 修复：恢复任务方法（使用传入的 labelColorMap）

// useTaskFlow.js
const restoreTask = async (taskId) => {
  try {
    console.log('🔄 开始恢复任务:', taskId)
    const response = await fetch(`http://localhost:8000/api/tasks/${taskId}`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    if (data.task) {
      // ✅ 关键修复：转换字段名以匹配前端期望的驼峰命名
      const taskInfo = {
        ...data.task,
        imageUrl: data.task.image_url,              // 转换下划线为驼峰
        imageStoragePath: data.task.image_storage_path,
        projectId: data.task.project_id,
        yoloVersion: data.task.yolo_version
      }
      
      // 设置当前任务（使用转换后的对象）
      store.setCurrentTask(taskInfo)
      
      // 处理标注中的颜色信息
      if (data.annotations && data.annotations.length > 0) {
        data.annotations.forEach(ann => {
          if (ann.color && ann.label && !labelColorMap.has(ann.label)) {
            labelColorMap.set(ann.label, ann.color)
          }
        })
      }
      
      store.setAnnotations(data.annotations || [])
      console.log('✅ 任务恢复成功:', taskInfo.imageUrl)
      return true
    }
    return false
  } catch (error) {
    console.error('❌ 恢复任务失败:', error)
    return false
  }
}

// 包装提交函数，添加清理逻辑
const submitWithCleanup = async () => {
  await submitAnnotations()
  // 提交成功后清理当前任务的预标注缓存
  if (store.currentTaskId) {
    clearPreAnnotations(store.currentTaskId)
  }
}

// 如果是保存草稿，也可以选择性清理（可选）
const saveDraftWithCleanup = async () => {
  await saveDraftHandler()
  // 保存草稿后可以选择保留或清理，这里选择保留以便刷新后恢复
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