<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>登录账号</h2>
      <form @submit.prevent="submit">
        <div>
          <label>用户名称</label>
          <input v-model.trim="form.username" type="text" required />
        </div>

        <div>
          <label>密码</label>
          <input v-model="form.password" type="password" required />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="switch-link">
        还没有账号？
        <router-link to="/register">去注册</router-link>
      </p>
    </div>
  </div>
</template>
    
<script setup lang="ts">
import { ref } from 'vue'
import { loginApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const router = useRouter()
const store = useUserStore()

const form = ref({
  username: '',
  password: '',
})

const loading = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    const { data } = await loginApi(form.value)
    store.login(data.user, data.access_token)
    router.push('/app/guide')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
}
.auth-card {
  width: min(92vw, 420px);
  padding: 32px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 20px 50px rgba(79, 70, 229, 0.12);
}
label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
}
input {
  width: 100%;
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #d4d4d8;
  border-radius: 12px;
}
button {
  width: 100%;
  padding: 12px 16px;
  border: none;
  border-radius: 12px;
  background: #4f46e5;
  color: white;
  font-weight: 600;
  cursor: pointer;
}
.error {
  color: #dc2626;
  margin-bottom: 12px;
}
.switch-link {
  margin-top: 16px;
  text-align: center;
}
</style>
