// composables/useAutoSave.js
import { ref } from 'vue'
import request from '@/api/request'
import { getCurrentUserId } from '@/utils/currentUser'
import { getTaskTrackingPayload, incrementTaskSaveCount } from '@/utils/taskWorkTracker'

export function useAutoSave(taskId, annotations) {
  const saving = ref(false)
  const lastSaved = ref(null)
  let saveTimeout = null

  const save = async () => {
    if (!taskId.value || annotations.value.length === 0) return
    
    saving.value = true
    try {
      incrementTaskSaveCount(taskId.value)
      await request.post(`/annotations/${taskId.value}`, {
        annotations: annotations.value,
        is_draft: true,
        user_id: getCurrentUserId(),
        ...(getTaskTrackingPayload(taskId.value) || {}),
      })
      lastSaved.value = new Date()
    } catch (e) {
      console.error('自动保存失败:', e)
    } finally {
      saving.value = false
    }
  }

  // 防抖保存，每3秒最多保存一次
  const debouncedSave = () => {
    if (saveTimeout) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(save, 3000)
  }

  return { saving, lastSaved, save: debouncedSave }
}
