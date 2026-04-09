<template>
  <div class="app-layout">
    <!-- 动态科技背景层 -->
    <div class="tech-background">
      <div class="particle-grid"></div>
      <div class="floating-orb orb-1"></div>
      <div class="floating-orb orb-2"></div>
      <div class="floating-orb orb-3"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部 Header - 科技玻璃 -->
    <header class="top-header">
      <div class="logo-area">
        <div class="logo-wrapper">
          <img src="@/assets/logo.svg" alt="Logo" class="logo-img" />
          <div class="logo-orbit"></div>
          <div class="logo-glow"></div>
        </div>
        <span class="logo-text">Image-cap</span>
      </div>
      <div class="header-right">
        <div class="header-actions">
          <button class="header-btn magnetic-btn" @click="toggleFullscreen" title="全屏">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
            <span class="btn-ripple"></span>
          </button>
          <button class="header-btn magnetic-btn" @click="refreshPage" title="刷新">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span class="btn-ripple"></span>
          </button>
        </div>
        <div class="user-status">
          <span class="status-dot"></span>
          <span class="status-text">{{ userStore.user?.is_active ? '在线' : '离线' }}</span>
          <span class="status-wave"></span>
        </div>
      </div>
    </header>

    <div class="main-container">
      <!-- 左侧侧边栏 - 科技光感 -->
      <aside class="tech-sidebar" :class="{ hidden: isFullscreen }">
        <div class="sidebar-glow"></div>
        <nav class="sidebar-menu">
          <router-link
            v-for="(item, index) in menuItems"
            :key="item.path"
            :to="item.path"
            class="menu-item"
            :class="{ active: $route.path === item.path }"
            :style="{ '--delay': index * 0.05 + 's' }"
          >
            <div class="menu-icon-wrapper">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-html="item.icon"></svg>
            </div>
            <span class="menu-text">{{ item.label }}</span>
            <div class="menu-glow"></div>
          </router-link>
        </nav>

        <!-- 底部用户区域 -->
        <div class="sidebar-footer">
          <div class="user-card" @click="toggleUserMenu" :class="{ active: showUserMenu }">
            <div class="avatar-wrapper">
              <img
                v-if="userStore.user?.avatar"
                :src="userStore.user.avatar"
                alt="avatar"
                class="user-avatar user-avatar--image"
              />
              <div v-else class="user-avatar">{{ userInitials }}</div>
              <div class="avatar-glow"></div>
              <div class="avatar-ring"></div>
            </div>
            <div class="user-info">
              <div class="user-name">{{ userName }}</div>
              <div class="user-role">{{ userRole }}</div>
            </div>
            <svg class="arrow-icon" :class="{ rotated: showUserMenu }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          <transition name="slide-up">
            <div v-if="showUserMenu" class="user-dropdown">
              <div class="dropdown-item" @click="goToProfile">
                <span class="dropdown-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <span>个人中心</span>
              </div>
              <div class="dropdown-item" @click="openTeamCreateDialog">
                <span class="dropdown-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </span>
                <span>团队创建</span>
              </div>
              <div class="divider"></div>
              <div class="dropdown-item danger" @click="handleLogout">
                <span class="dropdown-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                </span>
                <span>退出登录</span>
              </div>
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
      <div class="toolbar-trigger" v-show="!showFloatToolbar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="1" />
          <circle cx="19" cy="12" r="1" />
          <circle cx="5" cy="12" r="1" />
        </svg>
      </div>
      <div class="toolbar-content" v-show="showFloatToolbar">
        <button @click="exitFullscreen" title="退出全屏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
          </svg>
        </button>
        <button @click="goToAnnotate" title="标注">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 19l7-7 3 3-7 7-3-3z" />
            <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" />
          </svg>
        </button>
        <button @click="refreshPage" title="刷新">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 团队创建对话框 -->
    <teleport to="body">
      <transition name="fade-dialog">
        <div v-if="teamDialogVisible" class="team-dialog-mask" @click="closeTeamCreateDialog">
          <div class="team-dialog-panel" @click.stop>
            <div class="dialog-glow"></div>
            <div class="team-dialog-header">
              <div class="header-content">
                <div class="icon-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </div>
                <div>
                  <div class="team-dialog-title">新建团队</div>
                  <div class="team-dialog-subtitle">创建后将自动切换到新的团队空间</div>
                </div>
              </div>
              <button type="button" class="team-dialog-close" @click="closeTeamCreateDialog">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div class="team-dialog-body">
              <div class="team-field">
                <label class="team-field-label">团队名称</label>
                <div class="input-wrapper">
                  <input
                    v-model.trim="teamForm.name"
                    class="team-input"
                    type="text"
                    placeholder="请输入团队名称"
                    :class="{ error: teamDialogError }"
                  />
                  <div v-if="teamForm.name" class="input-clear" @click="teamForm.name = ''">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="15" y1="9" x2="9" y2="15" />
                      <line x1="9" y1="9" x2="15" y2="15" />
                    </svg>
                  </div>
                </div>
                <div v-if="teamDialogError" class="team-dialog-error">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {{ teamDialogError }}
                </div>
              </div>
            </div>

            <div class="team-dialog-footer">
              <button
                type="button"
                class="team-dialog-btn secondary"
                @click="closeTeamCreateDialog"
              >
                取消
              </button>
              <button 
                type="button" 
                class="team-dialog-btn primary" 
                @click="confirmTeamCreate"
                :disabled="!!teamDialogError || !teamForm.name.trim()"
              >
                <span>立即创建</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="js">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createOrganizationApi, logoutApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

defineOptions({
  name: 'ProjectLayoutView',
})

const router = useRouter()
const userStore = useUserStore()

const isFullscreen = ref(false)
const showUserMenu = ref(false)
const showFloatToolbar = ref(false)
const teamDialogVisible = ref(false)
const teamForm = reactive({ name: '' })

// 菜单配置
const menuItems = [
  {
    path: '/app/guide',
    label: '首页',
    icon: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />'
  },
  {
    path: '/app/project',
    label: '创建',
    icon: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" />'
  },
  {
    path: '/app/history',
    label: '列表',
    icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />'
  },
  {
    path: '/app/annotate',
    label: '标注',
    icon: '<path d="M12 19l7-7 3 3-7 7-3-3z" /><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" /><path d="M2 2l7.586 7.586" /><circle cx="11" cy="11" r="2" />'
  },
  {
    path: '/app/tasks',
    label: '任务',
    icon: '<path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />'
  },
  {
    path: '/app/training',
    label: '训练',
    icon: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />'
  },
  {
    path: '/app/profile',
    label: '个人中心',
    icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />'
  }
]

const userName = computed(() => userStore.user?.username || '匿名用户')
const userRole = computed(() => {
  const organization = userStore.currentOrganization || userStore.user?.organizations?.[0]
  return organization?.organization_type || '标注员'
})
const userInitials = computed(() => {
  const name = userName.value
  return name.length > 2 ? name.slice(0, 2).toUpperCase() : name.toUpperCase()
})

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

const refreshPage = () => window.location.reload()
const goToAnnotate = () => router.push('/app/annotate')
const toggleUserMenu = () => { showUserMenu.value = !showUserMenu.value }
const goToProfile = () => {
  showUserMenu.value = false
  router.push('/app/profile')
}

const teamDialogError = computed(() => {
  const name = teamForm.name.trim()
  if (!teamDialogVisible.value) return ''
  if (!name) return '请输入团队名称'
  const exists = (userStore.user?.organizations || []).some(
    (item) => item.organization_nickname.toLowerCase() === name.toLowerCase()
  )
  return exists ? '该名称已存在，请更换后再创建' : ''
})

const openTeamCreateDialog = () => {
  showUserMenu.value = false
  teamForm.name = ''
  teamDialogVisible.value = true
}

const closeTeamCreateDialog = () => {
  teamDialogVisible.value = false
}

const confirmTeamCreate = async () => {
  if (teamDialogError.value) return
  try {
    const response = await createOrganizationApi({
      organization_nickname: teamForm.name.trim(),
      organization_type: '团队',
    })
    userStore.refreshUserOrganizations(response.user)
    userStore.setCurrentOrganization(response.organization.organization_nickname)
    closeTeamCreateDialog()
    window.alert(`团队“${teamForm.name.trim()}”创建成功`)
  } catch (error) {
    window.alert(error?.response?.data?.detail || error?.message || '创建失败，请稍后重试')
  }
}

const handleLogout = async () => {
  showUserMenu.value = false
  if (!window.confirm('确定要退出登录吗？')) return
  try {
    await logoutApi()
  } catch {
  } finally {
    userStore.logout()
    router.push('/login')
  }
}

const handleClickOutside = (e) => {
  if (!e.target.closest('.sidebar-footer')) showUserMenu.value = false
}

// 磁性按钮效果
const initMagneticButtons = () => {
  const buttons = document.querySelectorAll('.magnetic-btn')
  buttons.forEach(btn => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect()
      const x = e.clientX - rect.left - rect.width / 2
      const y = e.clientY - rect.top - rect.height / 2
      btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`
    })
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'translate(0, 0)'
    })
  })
}

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  window.addEventListener('click', handleClickOutside)
  isFullscreen.value = !!document.fullscreenElement
  initMagneticButtons()
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f0f2f5;
  position: relative;
}

/* ===== 动态科技背景层 ===== */
.tech-background {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

/* 粒子网格 */
.particle-grid {
  position: absolute;
  inset: 0;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.15) 1px, transparent 0),
    linear-gradient(to right, rgba(59, 130, 246, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
  background-size: 40px 40px, 80px 80px, 80px 80px;
  animation: gridFloat 20s linear infinite;
}

@keyframes gridFloat {
  0% { transform: translate(0, 0); }
  100% { transform: translate(40px, 40px); }
}

/* 浮动光球 */
.floating-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.4;
  animation: orbFloat 15s ease-in-out infinite;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%);
  top: -100px;
  right: -100px;
  animation-delay: 0s;
}

.orb-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.25) 0%, transparent 70%);
  bottom: 10%;
  left: -50px;
  animation-delay: -5s;
}

.orb-3 {
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%);
  top: 40%;
  right: 20%;
  animation-delay: -10s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* 扫描线 */
.scan-line {
  position: absolute;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.5) 50%, 
    transparent 100%);
  top: 0;
  animation: scanMove 8s linear infinite;
  opacity: 0.3;
}

@keyframes scanMove {
  0% { top: 0; opacity: 0; }
  10% { opacity: 0.3; }
  90% { opacity: 0.3; }
  100% { top: 100%; opacity: 0; }
}

/* ===== 顶部 Header - 科技玻璃 ===== */
.top-header {
  height: 64px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  z-index: 100;
  box-shadow: 
    0 4px 20px rgba(59, 130, 246, 0.05),
    0 1px 0 rgba(255, 255, 255, 0.8) inset;
  position: relative;
}

.top-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.4) 20%, 
    rgba(6, 182, 212, 0.4) 80%, 
    transparent 100%);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-wrapper {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-img {
  width: 32px;
  height: 32px;
  position: relative;
  z-index: 2;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.2));
}

/* Logo 光晕轨道 */
.logo-orbit {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1px solid rgba(59, 130, 246, 0.3);
  animation: orbit 4s linear infinite;
}

.logo-orbit::before {
  content: '';
  position: absolute;
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  top: -3px;
  left: 50%;
  transform: translateX(-50%);
  box-shadow: 0 0 10px #3b82f6, 0 0 20px #3b82f6;
}

.logo-glow {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%);
  animation: pulseGlow 2s ease-in-out infinite;
}

@keyframes orbit {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulseGlow {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.1); }
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 50%, #06b6d4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
  position: relative;
}

.logo-text::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6, transparent);
  opacity: 0;
  animation: textGlow 3s ease-in-out infinite;
}

@keyframes textGlow {
  0%, 100% { opacity: 0; }
  50% { opacity: 0.5; }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 磁性按钮 */
.magnetic-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #64748b;
  position: relative;
  overflow: hidden;
}

.magnetic-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.magnetic-btn svg {
  width: 18px;
  height: 18px;
  position: relative;
  z-index: 2;
  transition: transform 0.3s ease;
}

.magnetic-btn:hover svg {
  transform: scale(1.1);
}

/* 按钮涟漪效果 */
.btn-ripple {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--x, 50%) var(--y, 50%), 
    rgba(59, 130, 246, 0.3) 0%, 
    transparent 50%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.magnetic-btn:hover .btn-ripple {
  opacity: 1;
}

.user-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #10b981;
  font-weight: 600;
  padding: 8px 14px;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%);
  border-radius: 20px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  box-shadow: 
    0 2px 8px rgba(16, 185, 129, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  position: relative;
  overflow: hidden;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
  border-radius: 50%;
  position: relative;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-dot::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid #10b981;
  opacity: 0.3;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.5; }
  100% { transform: scale(2); opacity: 0; }
}

.status-wave {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  animation: statusWave 2s ease-out infinite;
}

@keyframes statusWave {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.2); opacity: 0; }
}

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* ===== 左侧侧边栏 - 科技光感 ===== */
.tech-sidebar {
  width: 240px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
  border-right: 1px solid rgba(59, 130, 246, 0.12);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px 0 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  box-shadow: 
    4px 0 24px rgba(59, 130, 246, 0.06),
    inset -1px 0 0 rgba(255, 255, 255, 0.8);
  position: relative;
  overflow: hidden;
}

/* 侧边栏顶部光晕 */
.tech-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.4) 20%, 
    rgba(6, 182, 212, 0.4) 80%, 
    transparent 100%);
}

.sidebar-glow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 200px;
  background: linear-gradient(180deg, 
    rgba(59, 130, 246, 0.05) 0%, 
    transparent 100%);
  pointer-events: none;
}

.tech-sidebar.hidden {
  transform: translateX(-100%);
  width: 0;
  padding: 0;
  overflow: hidden;
  opacity: 0;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  padding: 0 14px;
  gap: 4px;
}

/* 菜单项 - 科技感 */
.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  color: #64748b;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  margin: 0 2px;
  overflow: hidden;
  animation: slideIn 0.5s ease-out backwards;
  animation-delay: var(--delay, 0s);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 悬停光效 */
.menu-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(6, 182, 212, 0.08) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.menu-item:hover::before {
  opacity: 1;
}

.menu-item:hover {
  color: #3b82f6;
  transform: translateX(4px);
}

/* 激活状态 - 科技蓝光 */
.menu-item.active {
  color: #3b82f6;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%);
  font-weight: 600;
  box-shadow: 
    0 4px 12px rgba(59, 130, 246, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

/* 左侧发光指示条 */
.menu-item.active::after {
  content: '';
  position: absolute;
  left: -14px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: linear-gradient(180deg, #3b82f6 0%, #06b6d4 100%);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.6);
  animation: indicatorPulse 2s ease-in-out infinite;
}

@keyframes indicatorPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 菜单项光晕 */
.menu-glow {
  position: absolute;
  inset: 0;
  border-radius: 12px;
  background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), 
    rgba(59, 130, 246, 0.15) 0%, 
    transparent 50%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.menu-item:hover .menu-glow {
  opacity: 1;
}

/* 图标容器 */
.menu-icon-wrapper {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.3s ease;
  flex-shrink: 0;
  background: rgba(100, 116, 139, 0.08);
  position: relative;
  z-index: 1;
}

.menu-item svg {
  width: 18px;
  height: 18px;
  stroke-width: 1.5;
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
}

/* 激活图标 - 发光效果 */
.menu-item.active .menu-icon-wrapper {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%);
  box-shadow: 0 0 16px rgba(59, 130, 246, 0.3);
}

.menu-item.active svg {
  color: #3b82f6;
  filter: drop-shadow(0 0 4px rgba(59, 130, 246, 0.5));
  animation: iconFloat 3s ease-in-out infinite;
}

@keyframes iconFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

.menu-text {
  letter-spacing: 0.3px;
  position: relative;
  z-index: 1;
}

/* ===== 底部用户区域 - 科技卡片 ===== */
.sidebar-footer {
  position: relative;
  padding: 0 14px;
  margin-top: auto;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(248, 250, 252, 0.8) 100%);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(59, 130, 246, 0.1);
  box-shadow: 
    0 4px 12px rgba(59, 130, 246, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  position: relative;
  overflow: hidden;
}

.user-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(6, 182, 212, 0.05) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.user-card:hover::before,
.user-card.active::before {
  opacity: 1;
}

.user-card:hover,
.user-card.active {
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow: 
    0 8px 24px rgba(59, 130, 246, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transform: translateY(-2px);
}

.avatar-wrapper {
  position: relative;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  position: relative;
  z-index: 2;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.user-avatar--image {
  object-fit: cover;
}

/* 头像光晕 */
.avatar-glow {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, transparent, #3b82f6, #06b6d4, transparent);
  opacity: 0.3;
  animation: rotate 3s linear infinite;
  z-index: 1;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 头像脉冲环 */
.avatar-ring {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 1px solid rgba(59, 130, 246, 0.2);
  animation: avatarPulse 2s ease-out infinite;
}

@keyframes avatarPulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.2); opacity: 0; }
}

.user-info {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.user-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}

.user-role {
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.arrow-icon {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  transition: all 0.3s ease;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.arrow-icon.rotated {
  transform: rotate(180deg);
  color: #3b82f6;
}

/* ===== 下拉菜单 - 科技玻璃 ===== */
.user-dropdown {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 72px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(20px);
  border-radius: 16px;
  box-shadow: 
    0 25px 50px rgba(59, 130, 246, 0.15),
    0 0 0 1px rgba(59, 130, 246, 0.1);
  padding: 10px;
  z-index: 50;
  border: 1px solid rgba(59, 130, 246, 0.15);
  animation: dropdownAppear 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes dropdownAppear {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.dropdown-item {
  padding: 12px 14px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #475569;
  font-weight: 500;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.dropdown-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.05) 50%, 
    transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.3s ease;
}

.dropdown-item:hover::before {
  transform: translateX(100%);
}

.dropdown-item:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(6, 182, 212, 0.08) 100%);
  color: #3b82f6;
}

.dropdown-item.danger {
  color: #ef4444;
}

.dropdown-item.danger:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.05) 100%);
  color: #dc2626;
}

.dropdown-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.dropdown-icon svg {
  width: 16px;
  height: 16px;
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.2), transparent);
  margin: 8px 0;
}

/* ===== 主内容区 ===== */
.content-area {
  flex: 1;
  overflow: auto;
  background: transparent;
  position: relative;
  z-index: 1;
}

.content-area.fullscreen {
  width: 100%;
}

/* ===== 全屏浮动工具栏 - 科技 ===== */
.floating-toolbar {
  position: fixed;
  right: 24px;
  bottom: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(20px);
  color: #475569;
  border-radius: 16px;
  padding: 10px;
  box-shadow: 
    0 20px 40px rgba(59, 130, 246, 0.15),
    0 0 0 1px rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.15);
  z-index: 1000;
  animation: toolbarFloat 3s ease-in-out infinite;
}

@keyframes toolbarFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.toolbar-trigger {
  padding: 8px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.toolbar-trigger:hover {
  opacity: 1;
}

.toolbar-trigger svg {
  width: 20px;
  height: 20px;
}

.toolbar-content {
  display: flex;
  gap: 6px;
}

.toolbar-content button {
  border: none;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  background: rgba(59, 130, 246, 0.08);
  color: #64748b;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toolbar-content button:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  transform: scale(1.05);
}

.toolbar-content button svg {
  width: 18px;
  height: 18px;
}

/* ===== 动画 ===== */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

/* ===== 团队对话框 - 科技 ===== */
.team-dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}

.team-dialog-panel {
  width: min(440px, 100%);
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: saturate(180%) blur(20px);
  border-radius: 20px;
  padding: 28px;
  box-shadow: 
    0 40px 80px rgba(59, 130, 246, 0.2),
    0 0 0 1px rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.15);
  animation: dialog-enter 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.dialog-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
  pointer-events: none;
}

@keyframes dialog-enter {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.team-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.icon-wrapper {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  flex-shrink: 0;
  border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  position: relative;
  overflow: hidden;
}

.icon-wrapper::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.3) 100%);
}

.icon-wrapper svg {
  width: 22px;
  height: 22px;
}

.team-dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
  letter-spacing: -0.3px;
}

.team-dialog-subtitle {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.team-dialog-close {
  border: none;
  background: rgba(100, 116, 139, 0.08);
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s ease;
}

.team-dialog-close:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  transform: rotate(90deg);
}

.team-dialog-close svg {
  width: 18px;
  height: 18px;
}

.team-dialog-body {
  display: grid;
  gap: 16px;
}

.team-field {
  display: grid;
  gap: 8px;
}

.team-field-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: 0.3px;
}

.input-wrapper {
  position: relative;
}

.team-input {
  width: 100%;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 14px 40px 14px 16px;
  font-size: 15px;
  font-weight: 500;
  color: #1f2937;
  transition: all 0.25s ease;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
}

.team-input::placeholder {
  color: #94a3b8;
}

.team-input:focus {
  outline: none;
  border-color: #3b82f6;
  background: #ffffff;
  box-shadow: 
    0 0 0 4px rgba(59, 130, 246, 0.1),
    0 4px 12px rgba(59, 130, 246, 0.1);
}

.team-input.error {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.03);
}

.input-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  cursor: pointer;
  color: #94a3b8;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-clear:hover {
  color: #64748b;
}

.input-clear svg {
  width: 14px;
  height: 14px;
}

.team-dialog-error {
  color: #ef4444;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.team-dialog-error svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.team-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.team-dialog-btn {
  border: none;
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.team-dialog-btn.secondary {
  background: rgba(100, 116, 139, 0.1);
  color: #475569;
}

.team-dialog-btn.secondary:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.team-dialog-btn.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  position: relative;
  overflow: hidden;
}

.team-dialog-btn.primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(255, 255, 255, 0.3) 50%, 
    transparent 100%);
  transition: left 0.5s ease;
}

.team-dialog-btn.primary:hover::before {
  left: 100%;
}

.team-dialog-btn.primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(59, 130, 246, 0.4);
}

.team-dialog-btn.primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.team-dialog-btn svg {
  width: 16px;
  height: 16px;
}

.fade-dialog-enter-active,
.fade-dialog-leave-active {
  transition: all 0.25s ease;
}

.fade-dialog-enter-from,
.fade-dialog-leave-to {
  opacity: 0;
}

.fade-dialog-enter-from .team-dialog-panel,
.fade-dialog-leave-to .team-dialog-panel {
  transform: scale(0.97) translateY(20px);
  opacity: 0;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .tech-sidebar {
    width: 200px;
  }
  
  .floating-orb {
    opacity: 0.2;
  }
}
</style>
