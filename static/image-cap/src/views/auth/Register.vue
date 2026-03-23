<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>注册账号</h2>
      <form @submit.prevent="submit">
        <div>
          <label>用户名称</label>
          <input v-model.trim="form.username" type="text" required />
        </div>

        <div>
          <label>组织昵称</label>
          <input
            v-model.trim="form.organization_nickname"
            type="text"
            placeholder="不填则自动创建默认组织"
          />
        </div>

        <div>
          <label>默认组织类型</label>
          <input value="个人" type="text" disabled />
        </div>

        <div>
          <label>密码</label>
          <input v-model="form.password" type="password" required />
        </div>

        <div>
          <label>确认密码</label>
          <input v-model="confirmPassword" type="password" required />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="switch-link">
        已有账号？
        <router-link :to="loginLink">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'AuthRegister' })
import { computed, ref } from 'vue'
import { registerApi } from '@/api/auth'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const confirmPassword = ref('')

const form = ref({
  username: '',
  organization_nickname: '',
  organization_type: '个人' as '个人' | '团队',
  password: '',
})

const loading = ref(false)
const error = ref('')
const redirectTarget = computed(() => String(route.query.redirect || '/app/guide'))
const loginLink = computed(() => ({
  path: '/login',
  query: route.query.redirect ? { redirect: redirectTarget.value } : {},
}))

const submit = async () => {
  error.value = ''
  if (form.value.password.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (form.value.password !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }

  loading.value = true
  try {
    await registerApi({
      ...form.value,
      organization_nickname: form.value.organization_nickname || undefined,
    })
    router.push(loginLink.value)
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : ''
    error.value = message || '注册失败'
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
  width: min(92vw, 460px);
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
input,
select {
  width: 100%;
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #d4d4d8;
  border-radius: 12px;
  background: #fff;
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
