import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { Ref } from 'vue'
import request from '@/api/request'
import { getCurrentUserId } from '@/utils/currentUser'
import { getTaskTrackingPayload, incrementTaskSaveCount } from '@/utils/taskWorkTracker'

console.log('🔧 正在初始化 Supabase...')

// 调试：显示所有环境变量
console.log('📋 环境变量列表:')
Object.keys(import.meta.env).forEach(key => {
  if (key.startsWith('VITE_')) {
    console.log(`  ${key}: ${import.meta.env[key]}`)
  }
})

// 使用环境变量或备用值（注意 .trim() 去除空格！）
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://dvratyhccontfhftxdcl.supabase.co'
const supabaseAnonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_ACJWlzQHLZjBrEguHvF0xg_3BJgxAaH').trim()

console.log('⚙️  最终配置:')
console.log('  URL:', supabaseUrl)
console.log('  Key 已加载:', !!import.meta.env.VITE_SUPABASE_ANON_KEY)

// ✅ 创建客户端（有类型定义）
const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey)
console.log('✅ Supabase 客户端创建成功')

// 自动保存功能（添加类型）
// 自动保存功能（添加空值检查修复）
// ✅ 正确的类型定义
export function useAutoSave(
  taskIdRef: Ref<string | null | undefined>,
  annotationsRef: Ref<any[] | null | undefined>
) {
  const save = async () => {
    if (!taskIdRef?.value || !annotationsRef?.value?.length) return

    try {
      incrementTaskSaveCount(taskIdRef.value)
      await request.post(`/annotations/${taskIdRef.value}`, {
        annotations: annotationsRef.value,
        is_draft: true,
        user_id: getCurrentUserId(),
        ...(getTaskTrackingPayload(taskIdRef.value) || {}),
      })
      console.log('💾 自动保存成功')
    } catch (err) {
      console.error('自动保存失败:', err)
    }
  }

  return { save }
}

// ✅ 正确导出（有类型，不会undefined）
export { supabase }
export default supabase
