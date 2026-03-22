<template>
  <div class="home">
    <!-- 顶部栏 -->
    <header class="header">
      <div class="logo">
        <img src="/image/logo.jpg" alt="logo" />
      </div>

      <div class="auth-actions">
        <!-- 未登录 -->
        <template v-if="!userStore.isLogin">
          <a @click="openLogin">登录</a>
          <span class="divider">|</span>
          <a @click="openRegister">注册</a>
        </template>

        <!-- 已登录 -->
        <template v-else>
          <div class="user-chip">
            <img :src="userStore.user?.avatar" alt="avatar" class="user-chip__avatar" />
            <span class="username">{{ userStore.user?.username }}</span>
          </div>
          <span class="divider">|</span>
          <a @click="logout">退出</a>
        </template>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main">
      <div class="left">
        <button class="create-btn" @click="goCreate">+ 创建项目</button>
      </div>

      <div class="right">
        <img src="/image/star.jpg" alt="系统说明图" class="home-image" />

        <div class="intro">
          <h2>协同标注平台</h2>
          <p>支持多人协作标注，灵活的任务流转机制，提供项目进度可视化与结果统一管理能力。</p>
        </div>
      </div>
    </main>
  </div>

  <div v-if="drawerVisible" class="mask" @click="closeDrawer" />

  <div class="drawer" :class="{ open: drawerVisible }">
    <div class="form-wrapper">
      <div class="form-container">
        <h2 class="form-title">{{ drawerMode === 'login' ? '登录' : '注册' }}</h2>

        <div v-if="drawerMode === 'login'" class="form">
          <input v-model.trim="loginForm.username" placeholder="用户名称" />
          <input v-model="loginForm.password" type="password" placeholder="密码" />
          <div v-if="loginError" class="error">{{ loginError }}</div>
          <button @click="submitLogin" :disabled="loginLoading">
            {{ loginLoading ? '登录中...' : '登录' }}
          </button>
          <button class="link" @click="drawerMode = 'register'">去注册</button>
        </div>

        <div v-else class="form">
          <input v-model.trim="registerForm.username" placeholder="用户名称" />
          <input v-model.trim="registerForm.organization_nickname" placeholder="组织昵称（选填）" />
          <select v-model="registerForm.organization_type">
            <option value="个人">个人</option>
            <option value="团队">团队</option>
          </select>
          <input v-model="registerForm.password" type="password" placeholder="密码" />
          <input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" />
          <div v-if="registerError" class="error">{{ registerError }}</div>
          <button @click="submitRegister" :disabled="registerLoading">
            {{ registerLoading ? '注册中...' : '注册' }}
          </button>
          <button class="link" @click="drawerMode = 'login'">返回登录</button>
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

const logout = async () => {
  try {
    await logoutApi()
  } catch {
    // 忽略服务端退出失败，仍清理前端状态
  } finally {
    userStore.logout()
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
    const { data } = await loginApi(loginForm.value)
    userStore.login(data.user, data.access_token)

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
  height: 100vh;
  background: radial-gradient(circle at 20% 30%, #ffffff 0%, #e6e9ff 40%, #d5d9ff 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部栏 */
.header {
  height: 64px;
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.6);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
}

.logo img {
  height: 36px;
}
.auth-actions {
  display: flex;
  align-items: center;
}
.auth-actions a {
  color: #555;
  text-decoration: none;
  margin: 0 8px;
  transition: all 0.2s ease;
  cursor: pointer;
}
.auth-actions a:hover {
  color: #7a6efc;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-chip__avatar {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  object-fit: cover;
}
.username {
  font-weight: 600;
  color: #111827;
}
.divider {
  color: #9ca3af;
}
.main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 64px;
}
.left {
  width: 30%;
}
.right {
  width: 60%;
  display: flex;
  align-items: center;
  gap: 28px;
}
.create-btn {
  padding: 14px 28px;
  border: none;
  border-radius: 14px;
  background: #4f46e5;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 16px 30px rgba(79, 70, 229, 0.2);
}
.home-image {
  width: min(420px, 50%);
  border-radius: 24px;
  object-fit: cover;
}
.intro {
  max-width: 420px;
}
.intro h2 {
  font-size: 36px;
  margin-bottom: 12px;
}
.intro p {
  color: #4b5563;
  line-height: 1.8;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 99;
}
.drawer {
  position: fixed;
  top: 0;
  right: -440px;
  width: min(440px, 100vw);
  height: 100vh;
  background: #fff;
  transition: right 0.28s ease;
  z-index: 100;
  box-shadow: -10px 0 40px rgba(15, 23, 42, 0.16);
}
.drawer.open {
  right: 0;
}
.form-wrapper {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.form-container {
  width: 100%;
}
.form-title {
  margin-bottom: 20px;
  font-size: 28px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form input,
.form select {
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #d1d5db;
}
.form button {
  padding: 12px 16px;
  border: none;
  border-radius: 12px;
  background: #4f46e5;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.form .link {
  background: transparent;
  color: #4f46e5;
}
.error {
  color: #dc2626;
  font-size: 14px;
}
@media (max-width: 960px) {
  .main {
    flex-direction: column;
    justify-content: center;
    padding: 32px;
    gap: 32px;
  }
  .left,
  .right {
    width: 100%;
  }
  .right {
    flex-direction: column;
  }
  .home-image {
    width: 100%;
    max-width: 460px;
  }
}
</style>
