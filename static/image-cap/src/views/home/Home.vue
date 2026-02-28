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
          <span class="username">
            {{ userStore.user?.username }}
          </span>
          <span class="divider">|</span>
          <a @click="logout">退出</a>
        </template>
      </div>



    </header>

    <!-- 主体内容 -->
    <main class="main">
        <!-- 左侧 -->
        <div class="left">
            <button class="create-btn" @click="goCreate">
              + 创建项目
            </button>

        </div>

        <!-- 右侧 -->
        <div class="right">
        <img
            src="/image/star.jpg"
            alt="系统说明图"
            class="home-image"
        />

        <div class="intro">
            <h2>协同标注平台</h2>
            <p>
            支持多人协作标注，灵活的任务流转机制，
            提供项目进度可视化与结果统一管理能力。
            </p>
        </div>
        </div>

    </main>
  </div>

  <!-- 遮罩 -->
<div
  v-if="drawerVisible"
  class="mask"
  @click="closeDrawer"
/>

<!-- 抽屉 -->
<div
  class="drawer"
  :class="{ open: drawerVisible }"
>
  <!-- 表单容器 -->
  <div class="form-wrapper">
    <div class="form-container">
      <h2 class="form-title">{{ drawerMode === 'login' ? '登录' : '注册' }}</h2>

      <!-- 登录表单 -->
      <div v-if="drawerMode === 'login'" class="form">
        <input v-model="loginForm.username" placeholder="账号" />
        <input v-model="loginForm.password" type="password" placeholder="密码" />

        <div v-if="loginError" class="error">{{ loginError }}</div>

        <button @click="submitLogin" :disabled="loginLoading">
            {{ loginLoading ? '登录中...' : '登录' }}
        </button>

        <button class="link" @click="drawerMode = 'register'">
            去注册
        </button>
      </div>

      <!-- 注册表单 -->
      <div v-else class="form">
        <input v-model="registerForm.username" placeholder="账号" />
        <input v-model="registerForm.password" type="password" placeholder="密码" />
        <input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" />

        <div v-if="registerError" class="error">{{ registerError }}</div>

        <button @click="submitRegister" :disabled="registerLoading">
            {{ registerLoading ? '注册中...' : '注册' }}
        </button>

        <button class="link" @click="drawerMode = 'login'">
            返回登录
        </button>
      </div>
    </div>
  </div>
</div>




</template>

<script setup lang="ts">
import { ref } from 'vue'
import { loginApi, registerApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const logout = () => {
  userStore.logout()
}

const router = useRouter()

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
}

// ===== 登录表单 =====
const loginForm = ref({
  username: '',
  password: ''
})
const loginError = ref('')
const loginLoading = ref(false)

// ===== 注册表单 =====
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})
const registerError = ref('')
const registerLoading = ref(false)

// 登录
const submitLogin = async () => {
  loginError.value = ''
  if (!loginForm.value.username.trim()) return loginError.value = '请输入账号'
  if (!loginForm.value.password) return loginError.value = '请输入密码'

  if (loginLoading.value) return
  try {
    loginLoading.value = true
    const res = await loginApi(loginForm.value)
    
    // 保存 token
    localStorage.setItem('token', res.data.access_token)
    
    // 更新 store 用户信息
    userStore.login(res.data.user, res.data.access_token)

    drawerVisible.value = false
  } catch (e: any) {
    loginError.value = e?.response?.data?.detail || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

// 注册
const submitRegister = async () => {
  registerError.value = ''
  const { username, password, confirmPassword } = registerForm.value
  if (!username.trim()) return registerError.value = '请输入账号'
  if (!password) return registerError.value = '请输入密码'
  if (password.length < 6) return registerError.value = '密码至少 6 位'
  if (password !== confirmPassword) return registerError.value = '两次密码不一致'

  if (registerLoading.value) return
  try {
    registerLoading.value = true
    await registerApi({ username, password })
    drawerMode.value = 'login' // 注册成功跳转登录
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
  background: #a19fdc;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 关键 */
}


/* 顶部栏 */
.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
}

.logo img {
  height: 36px;
}

.auth-actions a {
  color: #333;
  text-decoration: none;
  margin: 0 6px;
}

.divider {
  margin: 0 4px;
}

/* 主体 */
.main {
  height: calc(100vh - 64px); /* 精确剩余高度 */
  display: grid;
  grid-template-columns: 1fr 2fr;
  padding: 32px;   /* 建议略减 */
  gap: 32px;
  box-sizing: border-box; /* 非常重要 */
}


/* 左侧 */
.left {
  display: flex;
  align-items: center;
  justify-content: center;
}

.create-btn {
  padding: 16px 32px;
  font-size: 16px;
  border-radius: 24px;
  border: none;
  cursor: pointer;
  background: #fff;
}

/* 右侧 */
.right {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}


.home-image {
  max-width: 100%;
  max-height: 60%;  /* 给文字留空间 */
  object-fit: contain;
  border-radius: 16px;
}

.intro {
  margin-top: 16px;
  text-align: center;
  color: #333;
  max-width: 480px;
  font-size: 14px;
  line-height: 1.6;
}


/* 遮罩 */
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 10;
}

/* 抽屉 */
.drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 50vw;
  height: 100vh;
  background: #fff;
  z-index: 11;
  transform: translateX(100%);
  transition: transform 0.3s ease;
  padding: 32px;
  box-sizing: border-box;
}

.drawer.open {
  transform: translateX(0);
}

/* 抽屉内部包裹器，用于上下居中 */
.form-wrapper {
  height: 100%;                /* 占满抽屉高度 */
  display: flex;
  align-items: center;         /* 垂直居中 */
  justify-content: center;     /* 水平居中 */
}

/* 表单容器 */
.form-container {
  width: 50%;                  /* 占抽屉一半宽度 */
  padding: 32px;
  border: 1px solid #ddd;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  background: #fff;

  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;         /* 表单内容水平居中 */
}


/* 表单标题 */
.form-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

/* 表单 */
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;              /* 充满容器宽度 */
}

/* 输入框 */
.form input {
  padding: 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
  width: 100%;
}

.form input:focus {
  border-color: #7a6efc;
  box-shadow: 0 0 0 2px rgba(122, 110, 252, 0.2);
}

/* 按钮 */
.form button {
  padding: 12px;
  border: none;
  cursor: pointer;
  border-radius: 6px;
  background: #7a6efc;
  color: #fff;
  font-weight: 500;
}

.form button:disabled {
  background: #aaa;
  cursor: not-allowed;
}

/* 链接按钮 */
.form .link {
  background: none;
  color: #666;
  text-align: center;
  cursor: pointer;
}

/* 错误提示 */
.error {
  color: #f56c6c;
  font-size: 12px;
}

 


</style>
