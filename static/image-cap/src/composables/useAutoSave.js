// composables/useAutoSave.js
import { ref, watch } from 'vue'
import { supabase } from '@/supabase'

export function useAutoSave(taskId, annotations) {
  const saving = ref(false)
  const lastSaved = ref(null)
  let saveTimeout = null

  const save = async () => {
    if (!taskId.value || annotations.value.length === 0) return
    
    saving.value = true
    try {
      await supabase
        .from('drafts')
        .upsert({
          task_id: taskId.value,
          annotations_json: annotations.value,
          saved_at: new Date().toISOString(),
          user_id: 'current_user' // 实际应从auth获取
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