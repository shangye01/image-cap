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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <span class="logo-text">Image-cap</span>
      </div>

      <div class="auth-actions">
        <!-- 未登录 -->
        <template v-if="!userStore.isLogin">
          <button class="btn-text" @click="openLogin">登录</button>
          <button class="btn-primary" @click="openRegister">免费注册</button>
        </template>

        <!-- 已登录 -->
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
        <div class="hero-content">
          <div class="badge">
            <span class="badge-dot"></span>
            <span>v2.0 全新上线</span>
          </div>
          
          <h1 class="hero-title">
            让图像标注
            <span class="gradient-text">更智能、更高效</span>
          </h1>
          
          <p class="hero-desc">
            新一代 AI 辅助协同标注平台，支持图像标注。
            实时协作、智能预标注、质量管控，一站式解决您的数据准备需求。
          </p>

          <div class="hero-stats">
            <div class="stat">
              <span class="stat-value">10x</span>
              <span class="stat-label">效率提升</span>
            </div>
            <div class="stat">
              <span class="stat-value">500+</span>
              <span class="stat-label">企业信赖</span>
            </div>
            <div class="stat">
              <span class="stat-value">99.9%</span>
              <span class="stat-label">服务可用性</span>
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

        <div class="hero-visual">
          <div class="image-card main-card">
            <img src="/image/star.jpg" alt="平台界面" />
            <div class="card-shine"></div>
          </div>
          <div class="floating-card card-1">
            <div class="mini-stat">
              <span class="mini-icon">⚡</span>
              <div>
                <div class="mini-value">2.3s</div>
                <div class="mini-label">AI 预标注</div>
              </div>
            </div>
          </div>
          <div class="floating-card card-2">
            <div class="mini-stat">
              <span class="mini-icon">👥</span>
              <div>
                <div class="mini-value">12</div>
                <div class="mini-label">在线协作者</div>
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
              <div class="ring-text">85%</div>
            </div>
            <div class="ring-label">项目进度</div>
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
        <div class="form-container">
          <div class="form-header">
            <h2 class="form-title">{{ drawerMode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
            <p class="form-subtitle">
              {{ drawerMode === 'login' ? '登录以继续您的标注工作' : '开始您的智能标注之旅' }}
            </p>
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
            <div v-if="loginError" class="error">{{ loginError }}</div>
            <button class="submit-btn" @click="submitLogin" :disabled="loginLoading">
              <span v-if="loginLoading" class="spinner"></span>
              <span v-else>登录</span>
            </button>
            
            <div class="form-footer">
              <span>还没有账号？</span>
              <a @click="drawerMode = 'register'">立即注册</a>
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
                <label>组织类型</label>
                <select v-model="registerForm.organization_type">
                  <option value="个人">个人开发者</option>
                  <option value="团队">企业团队</option>
                </select>
              </div>
            </div>
            <div class="input-group">
              <label>密码</label>
              <input v-model="registerForm.password" type="password" placeholder="设置登录密码（至少6位）" />
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
              <a @click="drawerMode = 'login'">直接登录</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { loginApi, logoutApi, registerApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()
const dropdownOpen = ref(false)

const features = [
  { icon: '🎯', title: '精准标注', desc: '像素级标注精度，支持多种标注类型' },
  { icon: '🚀', title: 'AI 加速', desc: '智能预标注，效率提升 10 倍以上' },
  { icon: '🤝', title: '团队协作', desc: '实时同步，多人协作无障碍' },
  { icon: '📊', title: '数据洞察', desc: '可视化统计，项目进度一目了然' },
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
    drawerMode.value = 'login'
    drawerVisible.value = true
    return
  }
  router.push('/app/guide')
}

const drawerVisible = ref(false)
const drawerMode = ref<'login' | 'register'>('login')

const openLogin = () => {
  drawerMode.value = 'login'
  drawerVisible.value = true
}

const openRegister = () => {
  drawerMode.value = 'register'
  drawerVisible.value = true
}

const closeDrawer = () => {
  drawerVisible.value = false
  loginError.value = ''
  registerError.value = ''
}

// ===== 登录表单 =====
const loginForm = ref({ username: '', password: '' })
const loginError = ref('')
const loginLoading = ref(false)

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

// 登录
const submitLogin = async () => {
  loginError.value = ''
  if (!loginForm.value.username) return (loginError.value = '请输入用户名称')
  if (!loginForm.value.password) return (loginError.value = '请输入密码')
  if (loginLoading.value) return

  try {
    loginLoading.value = true
    const result = await loginApi(loginForm.value)
    userStore.login(result.user, result.access_token)

    drawerVisible.value = false
    router.push('/app/guide')
  } catch (e: any) {
    loginError.value = e?.response?.data?.detail || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

// 注册
const submitRegister = async () => {
  registerError.value = ''
  const { username, password, confirmPassword, organization_nickname, organization_type } =
    registerForm.value
  if (!username) return (registerError.value = '请输入用户名称')
  if (!password) return (registerError.value = '请输入密码')
  if (password.length < 6) return (registerError.value = '密码至少 6 位')
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
    drawerMode.value = 'login'
    loginForm.value.username = username
    registerForm.value.password = ''
    registerForm.value.confirmPassword = ''
  } catch (e: any) {
    registerError.value = e?.response?.data?.detail || '注册失败'
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #ffffff;
  position: relative;
  overflow-x: hidden;
  color: #1a202c;
}

/* 背景装饰 - 增加层次感 */
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
  opacity: 0.15;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 800px;
  height: 800px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -300px;
  right: -200px;
  animation-delay: 0s;
}

.orb-2 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -200px;
  left: -200px;
  animation-delay: -7s;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 40%;
  left: 60%;
  animation-delay: -14s;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(102, 126, 234, 0.15) 1px, transparent 0);
  background-size: 40px 40px;
  mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%);
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* 顶部栏 - 玻璃拟态 */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 72px;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.7);
  border-bottom: 1px solid rgba(102, 126, 234, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  z-index: 50;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
}

.logo-icon svg {
  width: 24px;
  height: 24px;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #1a202c 0%, #4a5568 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.auth-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-text {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #4a5568;
  font-size: 15px;
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
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

/* 用户下拉菜单 */
.user-dropdown {
  position: relative;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
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
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(102, 126, 234, 0.3);
}

.username {
  font-weight: 600;
  color: #1a202c;
  font-size: 14px;
}

.dropdown-arrow {
  width: 16px;
  height: 16px;
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
  min-width: 180px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
}

.dropdown-menu a {
  display: block;
  padding: 12px 16px;
  color: #4a5568;
  font-size: 14px;
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
  margin: 8px 0;
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

/* 主体内容 */
.main {
  padding: 140px 48px 100px;
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.hero-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 100px;
  align-items: center;
  margin-bottom: 120px;
}

.hero-content {
  animation: fadeInUp 0.8s ease-out;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.hero-title {
  font-size: 56px;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 24px;
  letter-spacing: -1.5px;
  color: #1a202c;
}

.gradient-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 18px;
  color: #64748b;
  line-height: 1.8;
  margin-bottom: 40px;
  max-width: 540px;
}

.hero-stats {
  display: flex;
  gap: 48px;
  margin-bottom: 48px;
}

.stat {
  display: flex;
  flex-direction: column;
  position: relative;
}

.stat:not(:last-child)::after {
  content: '';
  position: absolute;
  right: -24px;
  top: 50%;
  transform: translateY(-50%);
  height: 40px;
  width: 1px;
  background: linear-gradient(to bottom, transparent, rgba(102, 126, 234, 0.3), transparent);
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #1a202c 0%, #4a5568 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  font-size: 14px;
  color: #718096;
  margin-top: 4px;
  font-weight: 500;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.btn-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 18px 36px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
}

.btn-main:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 60px rgba(102, 126, 234, 0.5);
}

.btn-main svg {
  width: 20px;
  height: 20px;
  transition: transform 0.3s ease;
}

.btn-main:hover svg {
  transform: translateX(4px);
}

/* 视觉区域 */
.hero-visual {
  position: relative;
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.image-card {
  position: relative;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 
    0 25px 80px rgba(102, 126, 234, 0.15),
    0 10px 30px rgba(0, 0, 0, 0.1);
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
  100% { transform: translateX(100%); }
}

.floating-card {
  position: absolute;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 20px 50px rgba(102, 126, 234, 0.15);
}

.card-1 {
  top: -30px;
  right: -40px;
  animation: float-card 6s ease-in-out infinite;
}

.card-2 {
  bottom: 100px;
  left: -50px;
  animation: float-card 6s ease-in-out infinite 1s;
}

.card-3 {
  bottom: -30px;
  right: 60px;
  animation: float-card 6s ease-in-out infinite 2s;
}

@keyframes float-card {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-15px) rotate(2deg); }
}

.mini-stat {
  display: flex;
  align-items: center;
  gap: 14px;
}

.mini-icon {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  border: 1px solid rgba(102, 126, 234, 0.2);
}

.mini-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a202c;
}

.mini-label {
  font-size: 13px;
  color: #718096;
  font-weight: 500;
}

.progress-ring {
  width: 70px;
  height: 70px;
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
  font-size: 16px;
  font-weight: 700;
  color: #1a202c;
}

.ring-label {
  text-align: center;
  font-size: 13px;
  color: #718096;
  margin-top: 6px;
  font-weight: 500;
}

/* 特性展示 - 玻璃卡片 */
.features-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.feature-card {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 20px;
  padding: 32px 24px;
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
  transform: translateY(-8px);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 30px 60px rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.2);
}

.feature-card:hover::before {
  transform: scaleX(1);
}

.feature-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  margin: 0 auto 20px;
  border: 1px solid rgba(102, 126, 234, 0.15);
  transition: all 0.4s ease;
}

.feature-card:hover .feature-icon {
  transform: scale(1.1);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 12px;
}

.feature-card p {
  font-size: 14px;
  color: #64748b;
  line-height: 1.7;
  margin: 0;
}

/* 抽屉 */
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
  padding: 24px;
  display: flex;
  justify-content: flex-end;
}

.close-btn {
  width: 44px;
  height: 44px;
  border: none;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 12px;
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
  width: 20px;
  height: 20px;
}

.form-wrapper {
  padding: 0 48px 48px;
}

.form-header {
  margin-bottom: 40px;
}

.form-title {
  font-size: 36px;
  font-weight: 800;
  color: #1a202c;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.form-subtitle {
  font-size: 16px;
  color: #64748b;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
}

.input-group label .optional {
  color: #a0aec0;
  font-weight: 400;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form input,
.form select {
  width: 100%;
  padding: 16px 18px;
  border-radius: 14px;
  border: 2px solid #e2e8f0;
  background: #fff;
  color: #1a202c;
  font-size: 15px;
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

.error {
  padding: 14px 18px;
  background: rgba(220, 38, 38, 0.05);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 12px;
  color: #dc2626;
  font-size: 14px;
  font-weight: 500;
}

.submit-btn {
  padding: 18px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  margin-top: 8px;
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.3);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 24px;
  height: 24px;
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
  font-size: 15px;
  color: #64748b;
  margin-top: 8px;
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

/* 动画 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式 */
@media (max-width: 1024px) {
  .hero-section {
    grid-template-columns: 1fr;
    gap: 80px;
  }
  
  .hero-visual {
    order: -1;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .floating-card {
    display: none;
  }
  
  .features-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .header {
    padding: 0 24px;
  }
  
  .main {
    padding: 120px 24px 80px;
  }
  
  .hero-title {
    font-size: 40px;
  }
  
  .hero-stats {
    gap: 32px;
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
}
</style>