import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { Ref } from 'vue'

console.log('🔧 正在初始化 Supabase...')

// 调试：显示所有环境变量
console.log('📋 环境变量列表:')
Object.keys(import.meta.env).forEach(key => {
  if (key.startsWith('VITE_')) {
    console.log(`  ${key}: ${import.meta.env[key]}`)
  }
})

// 使用环境变量或备用值（注意 .trim() 去除空格！）
const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL || 'http://127.0.0.1:54321').trim()
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
      await supabase
        .from('drafts')
        .upsert({
          task_id: taskIdRef.value,
          annotations_json: annotationsRef.value,
          user_id: 'anonymous',
          saved_at: new Date().toISOString()
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