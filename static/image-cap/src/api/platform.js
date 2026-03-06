// 在 src/api/platform.js 中新增
class PlatformClient {
    constructor() {
      this.ws = null
      this.token = localStorage.getItem('platform_token')
    }
  
    // ✅ 1. 统一认证
    async authenticate(userId, password) {
      const res = await fetch('/platform/api/auth', {
        method: 'POST',
        body: JSON.stringify({ userId, password })
      })
      const { token } = await res.json()
      this.token = token
      localStorage.setItem('platform_token', token)
      this.connectWebSocket()
    }
  
    // ✅ 2. WebSocket实时同步任务状态
    connectWebSocket() {
      this.ws = new WebSocket(`ws://localhost:8000/platform/ws?token=${this.token}`)
      
      this.ws.onmessage = (event) => {
        const { type, data } = JSON.parse(event.data)
        
        if (type === 'TASK_ASSIGNED') {
          // 平台分配新任务，自动加载
          loadNextTask(data.taskId)
          notification.success('新任务已分配')
        }
        
        if (type === 'TASK_REVOKED') {
          // 任务被撤回
          if (confirm('当前任务已被管理员撤回，是否保存草稿？')) {
            saveDraftHandler()
          }
          store.clearCurrentTask()
        }
      }
    }
  
    // ✅ 3. 心跳上报标注进度
    startHeartbeat() {
      setInterval(() => {
        if (store.currentTaskId) {
          fetch('/platform/api/heartbeat', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.token}` },
            body: JSON.stringify({
              taskId: store.currentTaskId,
              progress: store.annotations.length,
              timestamp: Date.now()
            })
          })
        }
      }, 30000) // 每30秒
    }
  }
  
  export const platformClient = new PlatformClient()