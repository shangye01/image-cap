// composables/useTaskFlow.js
import { ref, nextTick } from 'vue'
import { supabase } from '@/supabase'
import { apiUrl, resolveAssetUrl } from '@/config/api'

export function useTaskFlow(store, imageObj, labelColorMap, dragTick) {  
  const taskLoading = ref(false)
  const submitLoading = ref(false)
  const taskError = ref('')
  const taskSuccess = ref('')

  // 加载测试图片
  // ========== 加载测试图片（完整修复版） ==========
const loadTestImage = async () => {
  console.log('🖼️ [loadTestImage] 开始加载测试图片...')
  taskLoading.value = true
  taskError.value = ''
  taskSuccess.value = ''
  
  try {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    
    // 等待图片完全加载（关键修复）
    await new Promise((resolve, reject) => {
      img.onload = () => {
        console.log('✅ [loadTestImage] 图片 onload 触发')
        console.log(`   尺寸: ${img.naturalWidth} x ${img.naturalHeight}`)
        console.log(`   complete: ${img.complete}`)
        resolve()
      }
      
      img.onerror = (e) => {
        console.error('❌ [loadTestImage] 图片加载失败:', e)
        reject(new Error('图片加载失败'))
      }
      
      // 5秒超时
      setTimeout(() => {
        if (!img.complete) {
          console.error('❌ [loadTestImage] 加载超时')
          reject(new Error('加载超时'))
        }
      }, 5000)
      
      // 添加时间戳防止 304 缓存
      const timestamp = Date.now()
      img.src = `/test.jpg?t=${timestamp}`
      console.log(`🔥 [loadTestImage] 设置 src: ${img.src}`)
    })

    // 确保图片已完全解码（关键）
    if (img.decode) {
      await img.decode()
      console.log('✅ [loadTestImage] 图片 decode 完成')
    }
    
    // 使用 shallowRef 赋值（关键修复）
    console.log('🔥 [loadTestImage] 赋值给 imageObj (shallowRef)')
    imageObj.value = img
    
    // 强制等待 Vue 更新
    await nextTick()
    
    // 触发重绘
    dragTick.value++
    console.log('✅ [loadTestImage] imageObj 赋值完成，dragTick:', dragTick.value)
    
    // 清空旧标注
    store.clearAnnotations()
    store.setCurrentTask({ 
      id: 'test', 
      imageUrl: `/test.jpg?t=${Date.now()}`,  // 也更新时间戳
      imageStoragePath: ''
    })
    
    taskSuccess.value = '✅ 测试图片加载成功'
    setTimeout(() => taskSuccess.value = '', 2000)
    
  } catch (error) {
    console.error('❌ [loadTestImage] 错误:', error)
    taskError.value = `❌ 加载失败: ${error.message}`
    setTimeout(() => taskError.value = '', 3000)
  } finally {
    taskLoading.value = false
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

      const img = new Image()
      img.crossOrigin = 'anonymous'

      await new Promise((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error('图片加载失败'))
        // ✅ 关键修复：修正语法错误，确保 src 被正确赋值
        img.src = resolveAssetUrl(data.image_url)
        setTimeout(() => reject(new Error('加载超时')), 10000)
      })
      
      imageObj.value = img
      
      store.setCurrentTask({
        id: data.id,
        projectId: data.project_id,
        imageUrl: resolveAssetUrl(data.image_url),
        imageStoragePath: data.image_storage_path,
        yoloVersion: data.yolo_version
      })
      
      await nextTick()
      if (dragTick) dragTick.value++
      
      loadAnnotations(data.id)
      taskSuccess.value = `✅ 任务 ${data.id} 加载成功`
      setTimeout(() => taskSuccess.value = '', 2000)
      
    } catch (e) {
      taskError.value = e.message || '加载任务失败'
      console.error(e)
    } finally {
      taskLoading.value = false
    }
  }

  // 加载标注数据
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
     const response = await fetch(apiUrl(`/api/annotations/${store.currentTaskId}`), {
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
     const response = await fetch(apiUrl(`/api/annotations/${store.currentTaskId}`), {
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

  const restoreTask = async (taskId) => {
    try {
      console.log('🔄 开始恢复任务:', taskId)
      const response = await fetch(apiUrl(`/api/tasks/${taskId}`))
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.task) {
        const taskInfo = {
          ...data.task,
          imageUrl: resolveAssetUrl(data.task.image_url),
          imageStoragePath: data.task.image_storage_path,
          projectId: data.task.project_id,
          yoloVersion: data.task.yolo_version
        }
        
        store.setCurrentTask(taskInfo)
        
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
    restoreTask
  }
}