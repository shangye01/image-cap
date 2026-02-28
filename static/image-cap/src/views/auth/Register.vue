<template>
  <div class="register-form">
    <h2>Register</h2>
    <form @submit.prevent="submit">
      <div>
        <label>Username:</label>
        <input v-model="form.username" type="text" required />
      </div>
      <div>
        <label>Password:</label>
        <input v-model="form.password" type="password" required />
      </div>
      <div v-if="error" style="color:red">{{ error }}</div>
      <button type="submit" :disabled="loading">
        {{ loading ? 'Registering...' : 'Register' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { registerApi } from '@/api/auth'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await registerApi(form.value)
    router.push('/login')  // 注册成功跳转登录页
  } catch (err: any) {
    error.value = err?.message || 'Register failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-form {
  width: 300px;
  margin: 50px auto;
}
.register-form div {
  margin-bottom: 12px;
}
button {
  width: 100%;
}
</style>
