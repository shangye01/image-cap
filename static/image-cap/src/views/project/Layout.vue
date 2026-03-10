<template>
  <div class="app-layout">
    <!-- 顶部 Header -->
    <header class="top-header">
      <div class="logo-area">
        <img src="@/assets/logo.svg" alt="Logo" class="logo-img" />
        <span class="logo-text">Image-cap</span>
      </div>
      <div class="header-right">
        <button class="header-btn" @click="toggleFullscreen" title="全屏">
          <span>{{ isFullscreen ? '⛶' : '⛶' }}</span>
        </button>
        <button class="header-btn" @click="refreshPage" title="刷新">
          <span>🔄</span>
        </button>
        <div class="user-status">
          <span class="status-dot"></span>
          <span>已登录</span>
        </div>
      </div>
    </header>

    <div class="main-container">
      <!-- 左侧白色侧边栏 -->
      <aside class="white-sidebar" :class="{ hidden: isFullscreen }">
        <nav class="sidebar-menu">
          <router-link to="/app/guide" class="menu-item" :class="{ active: $route.path === '/app/guide' }">
            <span class="menu-icon">🏠</span>
            <span class="menu-text">首页</span>
          </router-link>
          
          <router-link to="/app/project" class="menu-item" :class="{ active: $route.path === '/app/project' }">
            <span class="menu-icon">📋</span>
            <span class="menu-text">创建</span>
          </router-link>
          
          <router-link to="/app/history" class="menu-item" :class="{ active: $route.path === '/app/history' }">
            <span class="menu-icon">📋</span>
            <span class="menu-text">列表</span>
          </router-link>
          
          <router-link to="/app/annotate" class="menu-item" :class="{ active: $route.path === '/app/annotate' }">
            <span class="menu-icon">✏️</span>
            <span class="menu-text">标注</span>
          </router-link>
          
          <router-link to="/app/tasks" class="menu-item" :class="{ active: $route.path === '/app/tasks' }">
            <span class="menu-icon">📋</span>
            <span class="menu-text">任务</span>
          </router-link>
          
          <router-link to="/app/training" class="menu-item" :class="{ active: $route.path === '/app/training' }">
            <span class="menu-icon">🚀</span>
            <span class="menu-text">训练</span>
          </router-link>

          <router-link to="/app/profile" class="menu-item" :class="{ active: $route.path === '/app/profile' }">
            <span class="menu-icon">👤</span>
            <span class="menu-text">个人中心</span>
          </router-link>
        </nav>

        <!-- 底部用户区域 -->
        <div class="sidebar-footer">
          <div class="user-card" @click="toggleUserMenu">
            <div class="user-avatar">{{ userInitials }}</div>
            <div class="user-info">
              <div class="user-name">{{ userName }}</div>
              <div class="user-role">{{ userRole }}</div>
            </div>
            <span class="arrow">▼</span>
          </div>
          
          <!-- 下拉菜单 -->
          <transition name="slide-up">
            <div v-if="showUserMenu" class="user-dropdown">
              <div class="dropdown-item" @click="goToProfile">
                <span>👤</span> 个人中心
              </div>
              <div class="dropdown-item" @click="showSettings">
                <span>⚙️</span> 系统设置
              </div>
              <div class="divider"></div>
              <div class="dropdown-item danger" @click="handleLogout">
                <span>🚪</span> 退出登录
              </div>
            </div>
          </transition>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="content-area" :class="{ fullscreen: isFullscreen, 'annotate-page': $route.path === '/app/annotate' }">
        <router-view />
      </main>
    </div>

    <!-- 全屏浮动工具栏 -->
    <div 
      v-if="isFullscreen" 
      class="floating-toolbar"
      @mouseenter="showFloatToolbar = true"
      @mouseleave="showFloatToolbar = false"
    >
      <div class="toolbar-trigger" v-show="!showFloatToolbar">⋮⋮</div>
      <div class="toolbar-content" v-show="showFloatToolbar">
        <button @click="exitFullscreen" title="退出全屏">⛶</button>
        <button @click="goToAnnotate" title="标注">✏️</button>
        <button @click="refreshPage" title="刷新">🔄</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnnotationStore } from '@/stores/annotation'

const route = useRoute()
const router = useRouter()
const store = useAnnotationStore()

// 状态
const isFullscreen = ref(false)
const showUserMenu = ref(false)
const showFloatToolbar = ref(false)

// 用户信息
const userName = computed(() => store.userId || '匿名用户')
const userRole = computed(() => '标注员')
const userInitials = computed(() => {
  const name = userName.value
  return name.length > 2 ? name.slice(0, 2).toUpperCase() : name.toUpperCase()
})

// 全屏控制
const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    await document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    await document.exitFullscreen()
    isFullscreen.value = false
  }
}

const exitFullscreen = async () => {
  if (document.fullscreenElement) {
    await document.exitFullscreen()
  }
  isFullscreen.value = false
}

const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// 其他方法
const refreshPage = () => window.location.reload()
const goToAnnotate = () => router.push('/app/annotate')
const toggleUserMenu = () => { showUserMenu.value = !showUserMenu.value }
const goToProfile = () => { showUserMenu.value = false; router.push('/app/profile') }
const showSettings = () => { showUserMenu.value = false; alert('设置功能开发中...') }
const handleLogout = () => {
  showUserMenu.value = false
  if (confirm('确定要退出登录吗？')) {
    store.logout()
    router.push('/login')
  }
}

// 点击外部关闭菜单
const handleClickOutside = (e) => {
  if (!e.target.closest('.sidebar-footer')) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  window.addEventListener('click', handleClickOutside)
  isFullscreen.value = !!document.fullscreenElement
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  window.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* ===== 基础重置 ===== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* ===== 整体布局 ===== */
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

/* ===== 顶部 Header ===== */
.top-header {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  z-index: 100;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-img {
  width: 36px;
  height: 36px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  color: #1f1f1f;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: #f5f5f5;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.header-btn:hover {
  background: #e8e8e8;
}

.user-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #52c41a;
  font-weight: 500;
  margin-left: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #52c41a;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== 主容器 ===== */
.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧白色侧边栏 ===== */
.white-sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 0;
  transition: all 0.3s;
  flex-shrink: 0;
}

.white-sidebar.hidden {
  transform: translateX(-100%);
  width: 0;
  padding: 0;
  overflow: hidden;
}

/* 菜单区域 */
.sidebar-menu {
  display: flex;
  flex-direction: column;
  padding: 0 12px;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #666;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  cursor: pointer;
}

.menu-item:hover {
  background: #f5f7fa;
  color: #333;
}

.menu-item.active {
  background: #e6f0ff;
  color: #2b6de5;
  font-weight: 500;
}

.menu-icon {
  font-size: 20px;
  width: 24px;
  text-align: center;
}

/* 底部用户区域 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  margin-top: auto;
  position: relative;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.user-card:hover {
  background: #e8ecf1;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  overflow: hidden;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.arrow {
  font-size: 12px;
  color: #999;
  transition: transform 0.2s;
}

.user-card:hover .arrow {
  transform: rotate(180deg);
}

/* 下拉菜单 */
.user-dropdown {
  position: absolute;
  bottom: 100%;
  left: 16px;
  right: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
  padding: 8px;
  margin-bottom: 8px;
  z-index: 1000;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.dropdown-item.danger {
  color: #ff4d4f;
}

.dropdown-item.danger:hover {
  background: #fff1f0;
}

.divider {
  height: 1px;
  background: #f0f0f0;
  margin: 8px 0;
}

/* ===== 主内容区 ===== */
.content-area {
  flex: 1;
  overflow: auto;
  background: #f0f2f5;
  transition: all 0.3s;
  position: relative;
}

.content-area.fullscreen {
  margin-left: 0;
}

/* 关键：标注页面全屏，无 padding，让 AnnotateView 占满 */
.content-area.annotate-page {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-area.annotate-page > * {
  flex: 1;
  height: 100%;
}

/* ===== 全屏浮动工具栏 ===== */
.floating-toolbar {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 9999;
}

.toolbar-trigger {
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.toolbar-content {
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 8px;
  display: flex;
  gap: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.toolbar-content button {
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.toolbar-content button:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* ===== 动画 ===== */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* ===== 滚动条 ===== */
.content-area::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.content-area::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.content-area::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .white-sidebar {
    position: fixed;
    left: 0;
    top: 64px;
    height: calc(100vh - 64px);
    z-index: 99;
    transform: translateX(-100%);
  }
  
  .white-sidebar.open {
    transform: translateX(0);
  }
  
  .content-area {
    margin-left: 0;
  }
}
</style>