// 工作流系统对接接口
const API_BASE = '/api/workflow'

// 获取用户认证token（可从store或localStorage获取）
const getAuthHeader = () => {
  const token = localStorage.getItem('authToken') || ''
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
}

/**
 * 获取下一个待标注任务
 * @returns {Promise<Object>} 任务对象 {id, imageUrl, projectId, priority}
 */


/**
 * 提交标注结果
 * @param {Object} payload - 提交数据
 * @param {string} payload.taskId - 任务ID
 * @param {Array} payload.annotations - 标注数据
 * @param {string} payload.userId - 用户ID
 */




// ✅ 获取任务时从数据库读取
export const fetchNextTask = async () => {
    const response = await fetch(`/api/tasks/next?userId=${getUserId()}`)
    const data = await response.json()
    
    return {
      id: data.task.id,
      imageUrl: data.task.image_url,
      annotations: data.annotations || []
    }
  }
  
  // ✅ 提交时保存到数据库
  export const submitTaskResults = async (payload) => {
    const response = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: payload.taskId,
        annotations: payload.annotations,
        user_id: payload.userId
      })
    })
    return response.json()
  }
  
  // ✅ 保存草稿到数据库
  export const saveDraft = async (taskId, annotations) => {
    await fetch('/api/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        annotations: annotations,
        user_id: getUserId()
      })
    })
  }