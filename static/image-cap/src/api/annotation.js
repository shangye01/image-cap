// api/annotation.js

import axios from 'axios'

// ✅ 确保使用相对路径，Vite代理会转发到8000端口
const API_BASE = '/api'

/**
 * 预测标注
 * @param {FormData} formData - 包含图片文件的表单数据
 * @returns {Promise<Array>} - 返回标注数组
 * @throws {Error} - 当API调用失败时抛出错误
 */
export const predictAnnotations = async (formData) => {
  try {
    console.log('📤 发送预测请求...')
    
    const response = await axios.post(`${API_BASE}/predict`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
    
    const data = response.data || {}
    console.log('📥 API响应:', data)
    
    // ✅ 检查后端是否返回成功标志
    if (!data.success) {
      throw new Error(data.message || '后端返回失败状态')
    }
    
    // ✅ 检查 annotations 是否存在
    if (!data.annotations) {
      console.warn('⚠️ 后端未返回 annotations 字段:', data)
      throw new Error('后端未返回标注数据')
    }
    
    // ✅ 确保所有数值都是数字类型
    const annotations = data.annotations.map(ann => ({
      id: ann.id || `pred_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      x: Number(ann.x) || 0,
      y: Number(ann.y) || 0,
      width: Number(ann.width) || 0,
      height: Number(ann.height) || 0,
      label: ann.label || 'object',
      // ✅ 修复：置信度保持为数字类型
      confidence: Number(ann.confidence) || 0.5,
      color: ann.color || '#ff0000'
    }))
    
    console.log(`✅ 成功解析 ${annotations.length} 个标注`)
    return annotations
    
  } catch (error) {
    console.error('❌ API调用失败:', error)
    
    // ✅ 详细记录错误信息
    if (error.response) {
      // 服务器返回了错误状态码
      console.error('  状态码:', error.response.status)
      console.error('  响应数据:', error.response.data)
      console.error('  响应头:', error.response.headers)
      
      // 提取后端错误信息
      const serverMessage = error.response.data?.detail 
        || error.response.data?.message 
        || `服务器错误 (${error.response.status})`
      throw new Error(serverMessage)
      
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('  无响应，请求:', error.request)
      throw new Error('无法连接到后端服务器，请检查服务是否运行')
      
    } else {
      // 请求配置出错
      console.error('  请求配置错误:', error.message)
      throw new Error(`请求错误: ${error.message}`)
    }
  }
}

/**
 * 保存标注
 * @param {string} taskId - 任务ID
 * @param {Array} annotations - 标注数组
 * @param {boolean} isDraft - 是否为草稿
 */
export const saveAnnotations = async (taskId, annotations, isDraft = false) => {
  try {
    const response = await axios.post(`${API_BASE}/annotations/${taskId}`, {
      annotations,
      is_draft: isDraft,
      user_id: 'anonymous'
    }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    })
    
    return response.data
    
  } catch (error) {
    console.error('❌ 保存标注失败:', error)
    throw extractErrorMessage(error)
  }
}

/**
 * 获取任务详情
 * @param {string} taskId - 任务ID
 */
export const getTask = async (taskId) => {
  try {
    const response = await axios.get(`${API_BASE}/tasks/${taskId}`, {
      timeout: 30000
    })
    return response.data
    
  } catch (error) {
    console.error('❌ 获取任务失败:', error)
    throw extractErrorMessage(error)
  }
}

// ✅ 辅助函数：提取错误信息
function extractErrorMessage(error) {
  if (error.response?.data?.detail) {
    return new Error(error.response.data.detail)
  }
  if (error.response?.data?.message) {
    return new Error(error.response.data.message)
  }
  if (error.message) {
    return new Error(error.message)
  }
  return new Error('未知错误')
}