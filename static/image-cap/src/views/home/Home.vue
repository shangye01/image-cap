<template>
  <div class="home">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 顶部栏 -->
    <header class="header">
      <div class="logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12,12C10.5,8,8,5,6,4C4,3,2.5,4,3,6C3.5,8,5.5,10,8,11C10,11.5,11,12,12,12Z" fill="#9aa4e8"/>
            <path d="M12,12C13.5,8,16,5,18,4C20,3,21.5,4,21,6C20.5,8,18.5,10,16,11C14,11.5,13,12,12,12Z" fill="#5b6cf9"/>
            <path d="M12,12C10.5,16,8,19,6,20C4,21,2.5,20,3,18C3.5,16,5.5,14,8,13C10,12.5,11,12,12,12Z" fill="#9aa4e8"/>
            <path d="M12,12C13.5,16,16,19,18,20C20,21,21.5,20,21,18C20.5,16,18.5,14,16,13C14,12.5,13,12,12,12Z" fill="#5b6cf9"/>
          </svg>
        </div>
        <span class="logo-text"> 灵绘标注</span>
      </div>

      <div class="auth-actions">
        <template v-if="!userStore.isLogin">
          <button class="btn-text" @click="openLogin">登录</button>
          <button class="btn-primary" @click="openRegister">免费注册</button>
        </template>
        <template v-else>
          <div class="user-dropdown">
            <div class="user-chip" @click="toggleDropdown">
              <img :src="userStore.user?.avatar || '/image/default-avatar.png'" alt="avatar" class="user-chip__avatar" />
              <span class="username">{{ userStore.user?.username }}</span>
              <svg class="dropdown-arrow" :class="{ open: dropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </div>
            <transition name="dropdown">
              <div v-if="dropdownOpen" class="dropdown-menu">
                <a @click="goToDashboard">进入工作台</a>
                <a @click="goToSettings">账号设置</a>
                <div class="divider"></div>
                <a @click="logout" class="logout">退出登录</a>
              </div>
            </transition>
          </div>
        </template>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main">
      <div class="hero-section">
        <!-- 左侧文字区 -->
        <div class="hero-content">
          <div class="badge">
            <span class="badge-dot"></span>
            <span>v2.0 全新上线</span>
          </div>

          <h1 class="hero-title">
            让图像标注<br />
            <span class="gradient-text">更智能、更高效</span>
          </h1>

          <p class="hero-desc">
            新一代 AI 辅助协同标注平台，支持图像分类、目标检测、语义分割等多种标注任务。
            内置深度学习预标注引擎，实时多人协作，全流程质量管控，为您的 AI 项目提供一站式数据准备解决方案。
          </p>

          <div class="hero-stats">
            <div class="stat">
              <span class="stat-value">极速</span>
              <span class="stat-label">AI 智能预标注</span>
            </div>
            <div class="stat">
              <span class="stat-value">广泛</span>
              <span class="stat-label">企业级信赖选择</span>
            </div>
            <div class="stat">
              <span class="stat-value">稳定</span>
              <span class="stat-label">全天候服务保障</span>
            </div>
          </div>

          <div class="hero-actions">
            <button class="btn-main" @click="goCreate">
              <span>开始创建项目</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 右侧视觉区 -->
        <div class="hero-visual">
          <div class="image-card main-card">
            <img src="/image/star.jpg" alt="平台界面" />
            <div class="card-shine"></div>
          </div>

          <div class="floating-card card-1">
            <div class="mini-stat">
              <span class="mini-icon">⚡</span>
              <div>
                <div class="mini-value">AI 驱动</div>
                <div class="mini-label">智能预标注引擎</div>
              </div>
            </div>
          </div>

          <div class="floating-card card-2">
            <div class="mini-stat">
              <span class="mini-icon">👥</span>
              <div>
                <div class="mini-value">实时协作</div>
                <div class="mini-label">多人同步标注</div>
              </div>
            </div>
          </div>

          <div class="floating-card card-3">
            <div class="progress-ring">
              <svg viewBox="0 0 36 36">
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#667eea" />
                    <stop offset="100%" stop-color="#764ba2" />
                  </linearGradient>
                </defs>
                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="circle" stroke-dasharray="85, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div class="ring-text">高效</div>
            </div>
            <div class="ring-label">项目进度追踪</div>
          </div>
        </div>
      </div>

      <!-- 特性展示 -->
      <div class="features-section">
        <div class="feature-card" v-for="(feature, idx) in features" :key="idx">
          <div class="feature-icon">{{ feature.icon }}</div>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.desc }}</p>
        </div>
      </div>
    </main>

    <!-- 登录/注册抽屉 -->
    <transition name="fade">
      <div v-if="drawerVisible" class="mask" @click="closeDrawer" />
    </transition>

    <div class="drawer" :class="{ open: drawerVisible }">
      <div class="drawer-header">
        <button class="close-btn" @click="closeDrawer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="form-wrapper">
        <div class="form-header">
          <h2 class="form-title">{{ drawerMode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p class="form-subtitle">{{ drawerMode === 'login' ? '登录以继续您的标注工作' : '开始您的智能标注之旅' }}</p>
        </div>

        <div v-if="drawerMode === 'login'" class="form">
          <div class="input-group">
            <label>用户名称</label>
            <input v-model.trim="loginForm.username" placeholder="请输入用户名称" />
          </div>
          <div class="input-group">
            <label>密码</label>
            <input v-model="loginForm.password" type="password" placeholder="请输入密码" />
          </div>
          <div class="input-group">
            <label>验证码</label>
            <div class="captcha-row">
              <input
                v-model.trim="loginForm.captcha_code"
                class="captcha-code-input"
                maxlength="10"
                placeholder="请输入图中内容"
              />
              <button
                class="captcha-button"
                type="button"
                :disabled="loginCaptchaLoading"
                @click="refreshLoginCaptcha()"
              >
                <img v-if="loginCaptchaImage" :src="loginCaptchaImage" alt="验证码" class="captcha-image" />
                <span v-else>{{ loginCaptchaLoading ? '加载中...' : '刷新验证码' }}</span>
              </button>
            </div>
            <div class="captcha-tip">看不清？点击图片刷新</div>
          </div>
          <div v-if="loginError" class="error">{{ loginError }}</div>
          <button class="submit-btn" @click="submitLogin" :disabled="loginLoading || loginCaptchaLoading || !loginForm.captcha_id">
            <span v-if="loginLoading" class="spinner"></span>
            <span v-else>登录</span>
          </button>
          <div class="form-footer">
            <span>还没有账号？</span>
            <a @click="switchToRegisterMode">立即注册</a>
          </div>
        </div>

        <div v-else class="form">
          <div class="input-group">
            <label>用户名称</label>
            <input v-model.trim="registerForm.username" placeholder="设置您的用户名称" />
          </div>
          <div class="input-row">
            <div class="input-group">
              <label>组织昵称 <span class="optional">选填</span></label>
              <input v-model.trim="registerForm.organization_nickname" placeholder="您的组织名称" />
            </div>
            <div class="input-group">
              <label>默认组织类型</label>
              <input value="个人开发者" disabled />
            </div>
          </div>
          <div class="input-group">
            <label class="password-label">
              <span>密码</span>
              <button
                class="rule-trigger"
                type="button"
                :aria-expanded="showRegisterPasswordRules ? 'true' : 'false'"
                aria-label="查看密码规则"
                @click="showRegisterPasswordRules = !showRegisterPasswordRules"
              >
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
                  <path d="M12 10.2V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <circle cx="12" cy="7.5" r="1" fill="currentColor" />
                </svg>
              </button>
            </label>
            <input v-model="registerForm.password" type="password" placeholder="设置登录密码（至少8位，含字母和数字）" />
            <div v-if="showRegisterPasswordRules" class="password-rules">
              <div class="password-rules__title">密码规则</div>
              <ul class="password-rules__list">
                <li v-for="item in PASSWORD_POLICY_ITEMS" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="password-tip">{{ PASSWORD_POLICY_HINT }}</div>
          </div>
          <div class="input-group">
            <label>确认密码</label>
            <input v-model="registerForm.confirmPassword" type="password" placeholder="再次输入密码" />
          </div>
          <div v-if="registerError" class="error">{{ registerError }}</div>
          <button class="submit-btn" @click="submitRegister" :disabled="registerLoading">
            <span v-if="registerLoading" class="spinner"></span>
            <span v-else>创建账号</span>
          </button>
          <div class="form-footer">
            <span>已有账号？</span>
            <a @click="switchToLoginMode()">直接登录</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getCaptchaApi, loginApi, logoutApi, registerApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import {
  PASSWORD_POLICY_HINT,
  PASSWORD_POLICY_ITEMS,
  validatePasswordPolicy,
} from '@/utils/passwordPolicy'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()
const dropdownOpen = ref(false)

const features = [
  { icon: '🎯', title: '精准标注', desc: '支持矩形框、多边形、关键点等多种标注方式，像素级精度控制，满足计算机视觉全场景需求' },
  { icon: '🚀', title: 'AI 加速', desc: '基于深度学习的智能预标注引擎，自动识别目标物体，大幅缩短标注周期，让团队专注高价值工作' },
  { icon: '🤝', title: '团队协作', desc: '多人实时在线同步标注，内置评论与审核流程，角色分级管理，确保项目高效有序推进' },
  { icon: '📊', title: '数据洞察', desc: '可视化数据仪表盘，实时追踪标注进度与质量指标，支持自定义报表导出，辅助决策分析' },
]

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value
}

const goToDashboard = () => {
  router.push('/app/guide')
  dropdownOpen.value = false
}

const goToSettings = () => {
  dropdownOpen.value = false
}

const logout = async () => {
  try {
    await logoutApi()
  } catch {
    // 忽略服务端退出失败，仍清理前端状态
  } finally {
    userStore.logout()
    dropdownOpen.value = false
    router.push('/')
  }
}

const goCreate = () => {
  if (!userStore.isLogin) {
    openLogin()
    return
  }
  router.push('/app/guide')
}

const drawerVisible = ref(false)
const drawerMode = ref<'login' | 'register'>('login')

const openLogin = () => {
  drawerMode.value = 'login'
  drawerVisible.value = true
  void refreshLoginCaptcha()
}

const openRegister = () => {
  drawerMode.value = 'register'
  drawerVisible.value = true
  showRegisterPasswordRules.value = false
}

const closeDrawer = () => {
  drawerVisible.value = false
  loginError.value = ''
  registerError.value = ''
  loginForm.value.captcha_id = ''
  loginForm.value.captcha_code = ''
  loginCaptchaImage.value = ''
  showRegisterPasswordRules.value = false
}

// ===== 登录表单 =====
const loginForm = ref({ username: '', password: '', captcha_id: '', captcha_code: '' })
const loginError = ref('')
const loginLoading = ref(false)
const loginCaptchaImage = ref('')
const loginCaptchaLoading = ref(false)
const showRegisterPasswordRules = ref(false)

// ===== 注册表单 =====
const registerForm = ref({
  username: '',
  organization_nickname: '',
  organization_type: '个人' as '个人' | '团队',
  password: '',
  confirmPassword: '',
})
const registerError = ref('')
const registerLoading = ref(false)

const getActionErrorMessage = (err: unknown, fallback: string) => {
  if (typeof err === 'object' && err !== null) {
    const response = (err as { response?: { data?: { detail?: string; message?: string } } }).response
    const detail = response?.data?.detail || response?.data?.message
    if (detail) return detail
  }

  if (err instanceof Error && err.message) {
    return err.message
  }

  return fallback
}

const refreshLoginCaptcha = async (preserveError = false) => {
  loginCaptchaLoading.value = true
  if (!preserveError) {
    loginError.value = ''
  }

  try {
    const result = await getCaptchaApi()
    loginForm.value.captcha_id = result.captcha_id
    loginForm.value.captcha_code = ''
    loginCaptchaImage.value = result.image_data
  } catch (err: unknown) {
    loginForm.value.captcha_id = ''
    loginCaptchaImage.value = ''
    if (!preserveError) {
      loginError.value = getActionErrorMessage(err, '验证码加载失败，请稍后重试')
    }
  } finally {
    loginCaptchaLoading.value = false
  }
}

const switchToRegisterMode = () => {
  drawerMode.value = 'register'
  loginError.value = ''
  showRegisterPasswordRules.value = false
}

const switchToLoginMode = (username = '') => {
  drawerMode.value = 'login'
  loginError.value = ''
  if (username) {
    loginForm.value.username = username
  }
  void refreshLoginCaptcha()
}

// 登录
const submitLogin = async () => {
  loginError.value = ''
  if (!loginForm.value.username) return (loginError.value = '请输入用户名称')
  if (!loginForm.value.password) return (loginError.value = '请输入密码')
  if (!loginForm.value.captcha_code) return (loginError.value = '请输入验证码')
  if (loginLoading.value) return
  if (!loginForm.value.captcha_id) {
    await refreshLoginCaptcha()
    if (!loginForm.value.captcha_id) {
      loginError.value = '验证码加载失败，请刷新后重试'
      return
    }
  }

  try {
    loginLoading.value = true
    const result = await loginApi(loginForm.value)
    userStore.login(result.user, result.access_token)
    drawerVisible.value = false
    router.push('/app/guide')
  } catch (err: unknown) {
    loginError.value = getActionErrorMessage(err, '登录失败')
    await refreshLoginCaptcha(true)
  } finally {
    loginLoading.value = false
  }
}

// 注册
const submitRegister = async () => {
  registerError.value = ''
  const { username, password, confirmPassword, organization_nickname, organization_type } = registerForm.value
  if (!username) return (registerError.value = '请输入用户名称')
  if (!password) return (registerError.value = '请输入密码')
  const passwordError = validatePasswordPolicy(password)
  if (passwordError) return (registerError.value = passwordError)
  if (password !== confirmPassword) return (registerError.value = '两次密码不一致')
  if (registerLoading.value) return

  try {
    registerLoading.value = true
    await registerApi({
      username,
      password,
      organization_nickname: organization_nickname || undefined,
      organization_type,
    })
    switchToLoginMode(username)
    registerForm.value.password = ''
    registerForm.value.confirmPassword = ''
  } catch (err: unknown) {
    registerError.value = getActionErrorMessage(err, '注册失败')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  height: 100vh;
  background: #ffffff;
  position: relative;
  overflow: hidden;
  color: #1a202c;
  display: flex;
  flex-direction: column;
}

/* ========== 背景装饰 ========== */
.bg-decoration {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.12;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -200px;
  right: -150px;
  animation-delay: 0s;
}

.orb-2 {
  width: 450px;
  height: 450px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -150px;
  left: -150px;
  animation-delay: -7s;
}

.orb-3 {
  width: 350px;
  height: 350px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 40%;
  left: 55%;
  animation-delay: -14s;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(102, 126, 234, 0.12) 1px, transparent 0);
  background-size: 40px 40px;
  mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%);
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* ========== 顶部栏 ========== */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.7);
  border-bottom: 1px solid rgba(102, 126, 234, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  z-index: 50;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  box-sizing: border-box;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #6c6bc9 0%, #c586de 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.auth-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-text {
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: #4a5568;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 8px;
}

.btn-text:hover {
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.btn-primary {
  padding: 8px 20px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

/* 用户下拉菜单 */
.user-dropdown {
  position: relative;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 100px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.user-chip:hover {
  background: rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.3);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.user-chip__avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(102, 126, 234, 0.3);
}

.username {
  font-weight: 600;
  color: #1a202c;
  font-size: 13px;
}

.dropdown-arrow {
  width: 14px;
  height: 14px;
  color: #718096;
  transition: transform 0.3s ease;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 170px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
}

.dropdown-menu a {
  display: block;
  padding: 10px 14px;
  color: #4a5568;
  font-size: 13px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-menu a:hover {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.dropdown-menu .divider {
  height: 1px;
  background: rgba(102, 126, 234, 0.1);
  margin: 6px 0;
}

.dropdown-menu .logout {
  color: #dc2626;
}

.dropdown-menu .logout:hover {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.3s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ========== 主体内容 ========== */
.main {
  padding: 80px 40px 30px;
  max-width: 1280px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 0;
}

.hero-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 50px;
  align-items: center;
  margin-bottom: 30px;
  min-height: 0;
}

.hero-content {
  animation: fadeInUp 0.8s ease-out;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 18px;
  backdrop-filter: blur(10px);
}

.badge-dot {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.hero-title {
  font-size: 42px;
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 16px;
  letter-spacing: -1px;
  color: #1a202c;
}

.gradient-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 15px;
  color: #64748b;
  line-height: 1.7;
  margin-bottom: 24px;
  max-width: 520px;
}

.hero-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 28px;
}

.stat {
  display: flex;
  flex-direction: column;
  position: relative;
}

.stat:not(:last-child)::after {
  content: '';
  position: absolute;
  right: -16px;
  top: 50%;
  transform: translateY(-50%);
  height: 36px;
  width: 1px;
  background: linear-gradient(to bottom, transparent, rgba(102, 126, 234, 0.3), transparent);
}

.stat-value {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  font-size: 12px;
  color: #718096;
  margin-top: 3px;
  font-weight: 500;
}

.hero-actions {
  display: flex;
  gap: 14px;
}

.btn-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.4);
}

.btn-main:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 45px rgba(102, 126, 234, 0.5);
}

.btn-main svg {
  width: 18px;
  height: 18px;
  transition: transform 0.3s ease;
}

.btn-main:hover svg {
  transform: translateX(4px);
}

/* ========== 视觉区域 ========== */
.hero-visual {
  position: relative;
  animation: fadeInUp 0.8s ease-out 0.2s both;
  transform: scale(0.85);
  transform-origin: center;
}

.image-card {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(102, 126, 234, 0.15), 0 8px 20px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.1);
}

.image-card img {
  width: 100%;
  height: auto;
  display: block;
}

.card-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 40%,
    rgba(255, 255, 255, 0.2) 45%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0.2) 55%,
    transparent 60%
  );
  transform: translateX(-100%);
  animation: shine 8s infinite;
  pointer-events: none;
}

@keyframes shine {
  0%, 100% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
}

.floating-card {
  position: absolute;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 15px 40px rgba(102, 126, 234, 0.15);
}

.card-1 {
  top: -20px;
  right: -30px;
  animation: float-card 6s ease-in-out infinite;
}

.card-2 {
  bottom: 80px;
  left: -40px;
  animation: float-card 6s ease-in-out infinite 1s;
}

.card-3 {
  bottom: -20px;
  right: 50px;
  animation: float-card 6s ease-in-out infinite 2s;
}

@keyframes float-card {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-12px) rotate(2deg); }
}

.mini-stat {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mini-icon {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 1px solid rgba(102, 126, 234, 0.2);
}

.mini-value {
  font-size: 16px;
  font-weight: 700;
  color: #1a202c;
}

.mini-label {
  font-size: 11px;
  color: #718096;
  font-weight: 500;
}

.progress-ring {
  width: 56px;
  height: 56px;
  position: relative;
}

.progress-ring svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.circle-bg {
  fill: none;
  stroke: rgba(102, 126, 234, 0.1);
  stroke-width: 4;
}

.circle {
  fill: none;
  stroke: url(#gradient);
  stroke-width: 4;
  stroke-linecap: round;
  transition: stroke-dasharray 0.3s ease;
}

.ring-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 13px;
  font-weight: 700;
  color: #1a202c;
}

.ring-label {
  text-align: center;
  font-size: 11px;
  color: #718096;
  margin-top: 5px;
  font-weight: 500;
}

/* ========== 特性展示 ========== */
.features-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.feature-card {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 16px;
  padding: 18px 14px;
  text-align: center;
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transition: transform 0.4s ease;
}

.feature-card:hover {
  transform: translateY(-6px);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 50px rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.2);
}

.feature-card:hover::before {
  transform: scaleX(1);
}

.feature-icon {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin: 0 auto 10px;
  border: 1px solid rgba(102, 126, 234, 0.15);
  transition: all 0.4s ease;
}

.feature-card:hover .feature-icon {
  transform: scale(1.1);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
}

.feature-card h3 {
  font-size: 14px;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 6px;
}

.feature-card p {
  font-size: 11px;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

/* ========== 抽屉 ========== */
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  z-index: 99;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.drawer {
  position: fixed;
  top: 0;
  right: -480px;
  width: min(480px, 100vw);
  height: 100vh;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(30px);
  border-left: 1px solid rgba(102, 126, 234, 0.1);
  transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
  overflow-y: auto;
  box-shadow: -20px 0 60px rgba(0, 0, 0, 0.1);
}

.drawer.open {
  right: 0;
}

.drawer-header {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}

.close-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 10px;
  color: #667eea;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(102, 126, 234, 0.2);
  transform: rotate(90deg);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.form-wrapper {
  padding: 0 40px 40px;
}

.form-header {
  margin-bottom: 32px;
}

.form-title {
  font-size: 32px;
  font-weight: 800;
  color: #1a202c;
  margin-bottom: 10px;
  letter-spacing: -0.5px;
}

.form-subtitle {
  font-size: 15px;
  color: #64748b;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group label {
  font-size: 13px;
  font-weight: 600;
  color: #4a5568;
}

.password-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group label .optional {
  color: #a0aec0;
  font-weight: 400;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form input,
.form select {
  width: 100%;
  padding: 14px 16px;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  background: #fff;
  color: #1a202c;
  font-size: 14px;
  transition: all 0.3s ease;
}

.form input:focus,
.form select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.form input::placeholder {
  color: #a0aec0;
}

.form input:disabled {
  background: #f7fafc;
  color: #a0aec0;
  cursor: not-allowed;
}

.captcha-row {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 12px;
}

.captcha-code-input {
  min-width: 0;
}

.captcha-button {
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
  padding: 0;
  overflow: hidden;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.captcha-button:hover:not(:disabled) {
  border-color: #c7d2fe;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.08);
}

.captcha-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.captcha-image {
  display: block;
  width: 100%;
  height: 52px;
  object-fit: cover;
}

.captcha-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #718096;
}

.password-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #718096;
}

.rule-trigger {
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #6366f1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.rule-trigger svg {
  width: 14px;
  height: 14px;
}

.password-rules {
  margin-top: 8px;
  padding: 12px 14px;
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  background: rgba(238, 242, 255, 0.92);
}

.password-rules__title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #4338ca;
}

.password-rules__list {
  margin: 0;
  padding-left: 18px;
  color: #4c1d95;
  font-size: 12px;
  line-height: 1.6;
}

.error {
  padding: 12px 16px;
  background: rgba(220, 38, 38, 0.05);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  font-weight: 500;
}

.submit-btn {
  padding: 16px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  margin-top: 6px;
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.3);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 35px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 22px;
  height: 22px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-footer {
  text-align: center;
  font-size: 14px;
  color: #64748b;
  margin-top: 6px;
}

.form-footer a {
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  margin-left: 4px;
}

.form-footer a:hover {
  text-decoration: underline;
}

/* ========== 动画 ========== */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ========== 响应式 ========== */
@media (max-width: 1024px) {
  .hero-section {
    grid-template-columns: 1fr;
    gap: 40px;
  }

  .hero-visual {
    order: -1;
    max-width: 500px;
    margin: 0 auto;
    transform: scale(0.9);
  }

  .floating-card {
    display: none;
  }

  .features-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .home {
    overflow-y: auto;
    height: auto;
  }

  .header {
    padding: 0 20px;
    height: 56px;
  }

  .main {
    padding: 80px 20px 40px;
  }

  .hero-title {
    font-size: 32px;
  }

  .hero-stats {
    gap: 24px;
  }

  .stat:not(:last-child)::after {
    display: none;
  }

  .hero-actions {
    flex-direction: column;
  }

  .btn-main {
    width: 100%;
    justify-content: center;
  }

  .features-section {
    grid-template-columns: 1fr;
  }

  .form-wrapper {
    padding: 0 24px 24px;
  }

  .input-row {
    grid-template-columns: 1fr;
  }

  .captcha-row {
    grid-template-columns: 1fr;
  }
}
</style>
