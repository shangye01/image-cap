<template>
  <div class="app-layout">
    <!-- 顶部 Header -->
    <header class="top-header">
      <div class="logo-area">
        <img src="@/assets/logo.svg" alt="Logo" class="logo-img" />
        <span class="logo-text">Image-cap</span>
      </div>
      <div class="header-right">
        <button class="header-btn" @click="toggleFullscreen" title="全屏"><span>⛶</span></button>
        <button class="header-btn" @click="refreshPage" title="刷新"><span>🔄</span></button>
        <div class="user-status">
          <span class="status-dot"></span>
          <span>{{ userStore.user?.is_active ? '在线' : '离线' }}</span>
        </div>
      </div>
    </header>

    <div class="main-container">
      <!-- 左侧白色侧边栏 -->
      <aside class="white-sidebar" :class="{ hidden: isFullscreen }">
        <nav class="sidebar-menu">
          <router-link
            to="/app/guide"
            class="menu-item"
            :class="{ active: $route.path === '/app/guide' }"
            ><span class="menu-icon">🏠</span><span class="menu-text">首页</span></router-link
          >
          <router-link
            to="/app/project"
            class="menu-item"
            :class="{ active: $route.path === '/app/project' }"
            ><span class="menu-icon">📋</span><span class="menu-text">创建</span></router-link
          >
          <router-link
            to="/app/history"
            class="menu-item"
            :class="{ active: $route.path === '/app/history' }"
            ><span class="menu-icon">📋</span><span class="menu-text">列表</span></router-link
          >
          <router-link
            to="/app/annotate"
            class="menu-item"
            :class="{ active: $route.path === '/app/annotate' }"
            ><span class="menu-icon">✏️</span><span class="menu-text">标注</span></router-link
          >
          <router-link
            to="/app/tasks"
            class="menu-item"
            :class="{ active: $route.path === '/app/tasks' }"
            ><span class="menu-icon">📋</span><span class="menu-text">任务</span></router-link
          >
          <router-link
            to="/app/training"
            class="menu-item"
            :class="{ active: $route.path === '/app/training' }"
            ><span class="menu-icon">🚀</span><span class="menu-text">训练</span></router-link
          >
          <router-link
            to="/app/profile"
            class="menu-item"
            :class="{ active: $route.path === '/app/profile' }"
            ><span class="menu-icon">👤</span><span class="menu-text">个人中心</span></router-link
          >
        </nav>

        <!-- 底部用户区域 -->
        <div class="sidebar-footer">
          <div class="user-card" @click="toggleUserMenu">
            <img
              v-if="userStore.user?.avatar"
              :src="userStore.user.avatar"
              alt="avatar"
              class="user-avatar user-avatar--image"
            />
            <div v-else class="user-avatar">{{ userInitials }}</div>
            <div class="user-info">
              <div class="user-name">{{ userName }}</div>
              <div class="user-role">{{ userRole }}</div>
            </div>
            <span class="arrow">▼</span>
          </div>

          <!-- 下拉菜单 -->
          <transition name="slide-up">
            <div v-if="showUserMenu" class="user-dropdown">
              <div class="dropdown-item" @click="goToProfile"><span>👤</span> 个人中心</div>
              <div class="dropdown-item" @click="showSettings"><span>⚙️</span> 系统设置</div>
              <div class="divider"></div>
              <div class="dropdown-item danger" @click="handleLogout"><span>🚪</span> 退出登录</div>
            </div>
          </transition>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main
        class="content-area"
        :class="{ fullscreen: isFullscreen, 'annotate-page': $route.path === '/app/annotate' }"
      >
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
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { logoutApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 状态
const isFullscreen = ref(false)
const showUserMenu = ref(false)
const showFloatToolbar = ref(false)

// 用户信息
const userName = computed(() => userStore.user?.username || '匿名用户')
const userRole = computed(() => userStore.user?.organizations?.[0]?.organization_type || '标注员')
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
  if (document.fullscreenElement) await document.exitFullscreen()
  isFullscreen.value = false
}

const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// 其他方法
const refreshPage = () => window.location.reload()
const goToAnnotate = () => router.push('/app/annotate')
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}
const goToProfile = () => {
  showUserMenu.value = false
  router.push('/app/profile')
}
const showSettings = () => {
  showUserMenu.value = false
  window.alert('设置功能开发中...')
}
const handleLogout = async () => {
  showUserMenu.value = false
  if (!window.confirm('确定要退出登录吗？')) return
  try {
    await logoutApi()
  } catch {
    // 忽略服务端退出异常
  } finally {
    userStore.logout()
    router.push('/login')
  }
}

// 点击外部关闭菜单
const handleClickOutside = (e) => {
  if (!e.target.closest('.sidebar-footer')) showUserMenu.value = false
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
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
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
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}
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
  padding: 12px 14px;
  border-radius: 12px;
  color: #475569;
  text-decoration: none;
}
.menu-item.active,
.menu-item:hover {
  background: #eef2ff;
  color: #4338ca;
}
.sidebar-footer {
  position: relative;
  padding: 0 12px;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  background: #f8fafc;
  cursor: pointer;
}
.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.user-avatar--image {
  object-fit: cover;
  background: transparent;
}
.user-info {
  flex: 1;
  min-width: 0;
}
.user-name {
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-role {
  color: #6b7280;
  font-size: 13px;
}
.arrow {
  color: #94a3b8;
}
.user-dropdown {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 68px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.14);
  padding: 8px;
}
.dropdown-item {
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dropdown-item:hover {
  background: #f8fafc;
}
.dropdown-item.danger {
  color: #dc2626;
}
.divider {
  height: 1px;
  background: #e5e7eb;
  margin: 6px 0;
}
.content-area {
  flex: 1;
  overflow: auto;
  background: #f5f7fb;
}
.content-area.fullscreen {
  width: 100%;
}
.floating-toolbar {
  position: fixed;
  right: 20px;
  bottom: 20px;
  background: rgba(17, 24, 39, 0.88);
  color: white;
  border-radius: 16px;
  padding: 10px;
}
.toolbar-content {
  display: flex;
  gap: 8px;
}
.toolbar-content button {
  border: none;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
}
.toolbar-trigger {
  padding: 4px 8px;
}
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>