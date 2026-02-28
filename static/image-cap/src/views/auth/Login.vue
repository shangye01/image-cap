<template>
  <div class="login-form">
    <h2>Login</h2>

    <form @submit.prevent="submit">
      <div>
        <label>Username:</label>
        <input v-model="form.username" type="text" required />
      </div>

      <div>
        <label>Password:</label>
        <input v-model="form.password" type="password" required />
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Login' }}
      </button>
    </form>

    <!-- 注册入口 -->
    <p class="register-link">
      还没有账号？
      <router-link to="/register">去注册</router-link>
    </p>
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
  password: ''
})

const loading = ref(false)
const error = ref('')

// const submit = async () => {
//   error.value = ''
//   loading.value = true
//   try {
//     const res = await loginApi(form.value)
//     store.login(res.data)   // Pinia store login 方法
//     router.push('/')        // 登录成功跳转首页
//   } catch (err: any) {
//     error.value = err?.message || 'Login failed'
//   } finally {
//     loading.value = false
//   }
// }
</script>

<style scoped>
.login-form {
  width: 300px;
  margin: 50px auto;
}
.login-form div {
  margin-bottom: 12px;
}
.error {
  color: red;
}
.register-link {
  margin-top: 16px;
  text-align: center;
}
</style>
