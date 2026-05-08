// src/api/smartAnnotation.js
// 统一的智能预标注接口

import axios from 'axios'

const API_BASE = '/api'

/**
 * 统一的智能预标注接口
 * @param {string} taskId - 任务ID
 * @param {Object} options - 选项
 * @param {string[]} [options.keywords] - 关键词过滤列表（空数组表示识别所有）
 * @param {Function} [options.onProgress] - 进度回调
 * @returns {Promise<Array>} 标注数组（归一化坐标）
 */
export async function runSmartAnnotation(taskId, options = {}) {
  const { keywords = [], onProgress } = options
  
  console.log('🤖 调用智能预标注:', { taskId, keywords })
  
  if (onProgress) onProgress('正在识别...')
  
  try {
    const response = await axios.post(
      `${API_BASE}/tasks/${taskId}/predict`,
      { keywords },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 60000,
      }
    )
    
    const data = response.data
    
    if (!data.success) {
      throw new Error(data.message || '识别失败')
    }
    
    console.log('✅ 智能预标注成功:', {
      count: data.annotations?.length || 0,
      imageSize: { w: data.image_width, h: data.image_height },
    })
    
    if (onProgress) onProgress('识别完成')
    
    // 确保返回的标注包含原图尺寸信息
    const annotations = (data.annotations || []).map(ann => ({
      ...ann,
      original_width: data.image_width || ann.original_width || 640,
      original_height: data.image_height || ann.original_height || 640,
    }))
    
    return annotations
    
  } catch (error) {
    console.error('❌ 智能预标注失败:', error)
    
    let message = '识别失败'
    if (error.response?.data?.detail) {
      message = error.response.data.detail
    } else if (error.response?.data?.message) {
      message = error.response.data.message
    } else if (error.message) {
      message = error.message
    }
    
    throw new Error(message)
  }
}

/**
 * 批量智能预标注（用于项目创建时）
 * @param {string} projectId - 项目ID
 * @param {string[]} fileIds - 文件ID列表
 * @param {Object} options - 选项
 * @param {boolean} options.useKeywords - 是否使用关键词模式
 * @param {string[]} options.keywords - 关键词列表
 * @returns {Promise<Object>} 会话创建结果
 */
export async function createAnnotationSession(projectId, fileIds, options = {}) {
  const { useKeywords = false, keywords = [] } = options
  
  console.log('📤 创建标注会话:', {
    projectId,
    fileCount: fileIds.length,
    useKeywords,
    keywords,
  })
  
  try {
    const response = await axios.post(
      `${API_BASE}/projects/${projectId}/sessions`,
      {
        file_ids: fileIds,
        use_keywords: useKeywords,
        keywords: keywords,
      },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 120000, // 2分钟，因为包含图片下载和预标注
      }
    )
    
    console.log('✅ 会话创建成功:', {
      taskCount: response.data.tasks?.length,
      firstTask: response.data.first_task?.task_id,
    })
    
    return response.data
    
  } catch (error) {
    console.error('❌ 创建会话失败:', error)
    throw error
  }
}

/**
 * 保存预标注结果到 localStorage（用于前端缓存）
 * @param {string} taskId - 任务ID
 * @param {Array} annotations - 标注数组
 */
export function savePreAnnotationsToCache(taskId, annotations) {
  if (!taskId || !annotations?.length) return
  
  try {
    localStorage.setItem(
      `pre_annotations_${taskId}`,
      JSON.stringify(annotations)
    )
    console.log(`💾 预标注已缓存: ${taskId}`)
  } catch (e) {
    console.warn('缓存预标注失败:', e)
  }
}

/**
 * 从 localStorage 加载预标注
 * @param {string} taskId - 任务ID
 * @returns {Array|null} 标注数组或null
 */
export function loadPreAnnotationsFromCache(taskId) {
  if (!taskId) return null
  
  try {
    const data = localStorage.getItem(`pre_annotations_${taskId}`)
    return data ? JSON.parse(data) : null
  } catch (e) {
    console.warn('加载预标注缓存失败:', e)
    return null
  }
}

/**
 * 清理预标注缓存
 * @param {string} taskId - 任务ID
 */
export function clearPreAnnotationsCache(taskId) {
  if (!taskId) return
  localStorage.removeItem(`pre_annotations_${taskId}`)
}