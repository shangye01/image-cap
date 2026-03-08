<!-- views/ProfileView.vue -->
<template>
    <div class="profile-view">
      <div class="page-header">
        <h1>👤 个人中心</h1>
      </div>
  
      <div class="profile-content">
        <!-- 左侧信息卡片 -->
        <div class="info-section">
          <div class="profile-card">
            <div class="avatar-section">
              <div class="avatar-large">{{ userInitials }}</div>
              <h2>{{ userName }}</h2>
              <span class="role-tag">{{ userRole }}</span>
            </div>
            
            <div class="info-list">
              <div class="info-item">
                <span class="label">用户ID</span>
                <span class="value">{{ userId }}</span>
              </div>
              <div class="info-item">
                <span class="label">注册时间</span>
                <span class="value">2024-01-15</span>
              </div>
              <div class="info-item">
                <span class="label">最后登录</span>
                <span class="value">{{ lastLogin }}</span>
              </div>
            </div>
          </div>
  
          <div class="action-card">
            <button class="action-btn" @click="editProfile">
              <span>✏️</span> 编辑资料
            </button>
            <button class="action-btn" @click="changePassword">
              <span>🔐</span> 修改密码
            </button>
            <button class="action-btn danger" @click="handleLogout">
              <span>🚪</span> 退出登录
            </button>
          </div>
        </div>
  
        <!-- 右侧统计 -->
        <div class="stats-section">
          <div class="stats-grid">
            <div class="stat-box blue">
              <div class="stat-icon">📊</div>
              <div class="stat-num">{{ stats.totalAnnotations }}</div>
              <div class="stat-label">总标注数</div>
            </div>
            <div class="stat-box green">
              <div class="stat-icon">✅</div>
              <div class="stat-num">{{ stats.completedTasks }}</div>
              <div class="stat-label">完成任务</div>
            </div>
            <div class="stat-box orange">
              <div class="stat-icon">⏱️</div>
              <div class="stat-num">{{ stats.workingHours }}h</div>
              <div class="stat-label">工作时长</div>
            </div>
            <div class="stat-box purple">
              <div class="stat-icon">🎯</div>
              <div class="stat-num">{{ stats.accuracy }}%</div>
              <div class="stat-label">准确率</div>
            </div>
          </div>
  
          <!-- 最近活动 -->
          <div class="activity-card">
            <h3>🕐 最近活动</h3>
            <div class="activity-list">
              <div v-for="(item, index) in activities" :key="index" class="activity-item">
                <div class="activity-dot" :class="item.type"></div>
                <div class="activity-content">
                  <p>{{ item.text }}</p>
                  <span>{{ item.time }}</span>
                </div>
              </div>
            </div>
          </div>
  
          <!-- 快捷键说明 -->
          <div class="shortcuts-card">
            <h3>⌨️ 快捷键说明</h3>
            <div class="shortcut-grid">
              <div class="shortcut-item">
                <kbd>Delete</kbd>
                <span>删除选中标注</span>
              </div>
              <div class="shortcut-item">
                <kbd>F2</kbd>
                <span>修改标签</span>
              </div>
              <div class="shortcut-item">
                <kbd>Ctrl + Delete</kbd>
                <span>清除所有标注</span>
              </div>
              <div class="shortcut-item">
                <kbd>Esc</kbd>
                <span>取消选择</span>
              </div>
              <div class="shortcut-item">
                <kbd>F11</kbd>
                <span>全屏模式</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAnnotationStore } from '@/stores/annotation'
  
  const router = useRouter()
  const store = useAnnotationStore()
  
  const userName = computed(() => store.userId || '匿名用户')
  const userId = computed(() => store.userId || 'unknown')
  const userRole = ref('高级标注员')
  const userInitials = computed(() => {
    const name = userName.value
    return name.length > 2 ? name.slice(0, 2).toUpperCase() : name.toUpperCase()
  })
  const lastLogin = ref(new Date().toLocaleString('zh-CN'))
  
  const stats = ref({
    totalAnnotations: 1248,
    completedTasks: 156,
    workingHours: 48,
    accuracy: 96.5
  })
  
  const activities = ref([
    { type: 'success', text: '完成了任务 #TASK-2024-001', time: '10分钟前' },
    { type: 'info', text: '提交了 15 个标注', time: '2小时前' },
    { type: 'warning', text: '修改了标签 "person" 的颜色', time: '昨天' },
    { type: 'success', text: '训练了新模型 v2.1', time: '3天前' },
    { type: 'info', text: '登录系统', time: '3天前' }
  ])
  
  const editProfile = () => alert('编辑资料功能开发中...')
  const changePassword = () => alert('修改密码功能开发中...')
  const handleLogout = () => {
    if (confirm('确定要退出登录吗？')) {
      store.logout()
      router.push('/login')
    }
  }
  </script>
  
  <style scoped>
  .profile-view {
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .page-header {
    margin-bottom: 24px;
  }
  
  .page-header h1 {
    font-size: 24px;
    color: #1f1f1f;
    font-weight: 600;
  }
  
  .profile-content {
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 24px;
  }
  
  /* 左侧信息卡片 */
  .info-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  
  .profile-card {
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  
  .avatar-section {
    text-align: center;
    margin-bottom: 24px;
  }
  
  .avatar-large {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 36px;
    font-weight: 600;
    margin: 0 auto 16px;
  }
  
  .avatar-section h2 {
    font-size: 20px;
    color: #1f1f1f;
    margin-bottom: 8px;
  }
  
  .role-tag {
    display: inline-block;
    padding: 4px 16px;
    background: #e6f7ff;
    color: #1890ff;
    border-radius: 20px;
    font-size: 13px;
  }
  
  .info-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  
  .info-item:last-child {
    border-bottom: none;
  }
  
  .info-item .label {
    color: #666;
    font-size: 14px;
  }
  
  .info-item .value {
    color: #1f1f1f;
    font-size: 14px;
    font-weight: 500;
  }
  
  /* 操作按钮 */
  .action-card {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .action-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    border: none;
    background: #f5f7fa;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    color: #333;
    transition: all 0.2s;
  }
  
  .action-btn:hover {
    background: #e8ecf1;
  }
  
  .action-btn.danger {
    color: #ff4d4f;
  }
  
  .action-btn.danger:hover {
    background: #fff1f0;
  }
  
  /* 右侧统计 */
  .stats-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
  
  .stat-box {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    border-top: 3px solid;
  }
  
  .stat-box.blue { border-color: #1890ff; }
  .stat-box.green { border-color: #52c41a; }
  .stat-box.orange { border-color: #faad14; }
  .stat-box.purple { border-color: #722ed1; }
  
  .stat-icon {
    font-size: 28px;
    margin-bottom: 8px;
  }
  
  .stat-num {
    font-size: 28px;
    font-weight: 700;
    color: #1f1f1f;
    margin-bottom: 4px;
  }
  
  .stat-label {
    font-size: 13px;
    color: #666;
  }
  
  /* 最近活动 */
  .activity-card {
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  
  .activity-card h3 {
    font-size: 16px;
    color: #1f1f1f;
    margin-bottom: 20px;
    font-weight: 600;
  }
  
  .activity-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .activity-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  
  .activity-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
  }
  
  .activity-dot.success { background: #52c41a; }
  .activity-dot.info { background: #1890ff; }
  .activity-dot.warning { background: #faad14; }
  
  .activity-content {
    flex: 1;
  }
  
  .activity-content p {
    font-size: 14px;
    color: #333;
    margin-bottom: 4px;
  }
  
  .activity-content span {
    font-size: 12px;
    color: #999;
  }
  
  /* 快捷键说明 */
  .shortcuts-card {
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  
  .shortcuts-card h3 {
    font-size: 16px;
    color: #1f1f1f;
    margin-bottom: 20px;
    font-weight: 600;
  }
  
  .shortcut-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  .shortcut-item {
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 14px;
    color: #555;
  }
  
  kbd {
    padding: 6px 12px;
    background: #f5f5f5;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    font-family: monospace;
    font-size: 13px;
    min-width: 100px;
    text-align: center;
    box-shadow: 0 2px 0 #d9d9d9;
  }
  
  /* 响应式 */
  @media (max-width: 1024px) {
    .profile-content {
      grid-template-columns: 1fr;
    }
    
    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  @media (max-width: 640px) {
    .stats-grid {
      grid-template-columns: 1fr;
    }
    
    .shortcut-grid {
      grid-template-columns: 1fr;
    }
  }
  </style>