// composables/useTaskFlow.js
import { ref } from 'vue'
import { supabase } from '@/supabase'
import request from '@/api/request'

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
    img.src = '/test.jpg'

    img.onload = () => {
      imageObj.value = img
      store.clearAnnotations()
      taskSuccess.value = '测试图片加载成功'
      setTimeout(() => {
        taskSuccess.value = ''
      }, 2000)
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

      taskSuccess.value = `任务 ${data.id} 加载成功`
      setTimeout(() => {
        taskSuccess.value = ''
      }, 2500)
    } catch (e) {
      taskError.value = '没有可用任务'
      console.error(e)
    } finally {
      taskLoading.value = false
    }
  }

  // 加载项目任务
  const fetchProjectTask = async (projectId, taskId) => {
    if (!projectId || !taskId) return false

    taskLoading.value = true
    taskError.value = ''

    try {
      const data = await request.get(`/tasks/${taskId}`)

      if (data.task) {
        await loadTaskImage(data.task)

        if (data.annotations && data.annotations.length > 0) {
          data.annotations.forEach((ann) => {
            if (ann.color && ann.label && !labelColorMap.has(ann.label)) {
              labelColorMap.set(ann.label, ann.color)
            }
          })
        }

        store.setAnnotations(data.annotations || [])

        taskSuccess.value = `任务 ${taskId} 加载成功`
        setTimeout(() => {
          taskSuccess.value = ''
        }, 2500)

        return true
      }

      throw new Error('未找到任务数据')
    } catch (error) {
      console.error('加载项目任务失败:', error)
      taskError.value = error?.response?.data?.detail || error.message || '项目任务加载失败'
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
    taskError.value = ''

    try {
      const data = await request.post(`/annotations/${store.currentTaskId}`, {
        annotations: store.annotations,
        is_draft: false,
        user_id: store.userId || 'anonymous',
      })

      taskSuccess.value = data?.message || '✅ 提交成功！'
      setTimeout(() => {
        store.clearCurrentTask()
        imageObj.value = null
        taskSuccess.value = ''
      }, 2000)

      return data
    } catch (e) {
      taskError.value = `提交失败: ${e?.response?.data?.detail || e.message}`
      throw e
    } finally {
      submitLoading.value = false
    }
  }

  // 保存草稿
  const saveDraftHandler = async () => {
    if (!store.currentTaskId || store.annotations.length === 0) return

    taskError.value = ''

    try {
      await request.post(`/annotations/${store.currentTaskId}`, {
        annotations: store.annotations,
        is_draft: true,
        user_id: store.userId || 'anonymous',
      })

      taskSuccess.value = '💾 草稿已保存'
      setTimeout(() => {
        taskSuccess.value = ''
      }, 2000)
    } catch (e) {
      taskError.value = `保存草稿失败: ${e?.response?.data?.detail || e.message}`
      console.error(e)
    }
  }

  // 放弃任务
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

  // 恢复任务
  const restoreTask = async (taskId) => {
    try {
      console.log('🔄 开始恢复任务:', taskId)

      const data = await request.get(`/tasks/${taskId}`)

      if (data.task) {
        await loadTaskImage({
          ...data.task,
          imageUrl: data.task.image_url,
          imageStoragePath: data.task.image_storage_path,
        })

        if (data.annotations && data.annotations.length > 0) {
          data.annotations.forEach((ann) => {
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
    restoreTask,
  }
}