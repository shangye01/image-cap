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
          <label class="password-label">
            <span>密码</span>
            <button
              type="button"
              class="rule-trigger"
              :aria-expanded="showPasswordRules ? 'true' : 'false'"
              aria-label="查看密码规则"
              @click="showPasswordRules = !showPasswordRules"
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
                <path d="M12 10.2V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                <circle cx="12" cy="7.5" r="1" fill="currentColor" />
              </svg>
            </button>
          </label>
          <input v-model="form.password" type="password" required />
          <div v-if="showPasswordRules" class="password-rules">
            <div class="password-rules__title">密码规则</div>
            <ul class="password-rules__list">
              <li v-for="item in PASSWORD_POLICY_ITEMS" :key="item">{{ item }}</li>
            </ul>
          </div>
          <p class="password-tip">{{ PASSWORD_POLICY_HINT }}</p>
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
import {
  PASSWORD_POLICY_HINT,
  PASSWORD_POLICY_ITEMS,
  validatePasswordPolicy,
} from '@/utils/passwordPolicy'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const confirmPassword = ref('')
const showPasswordRules = ref(false)

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
  const passwordError = validatePasswordPolicy(form.value.password)
  if (passwordError) {
    error.value = passwordError
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
    if (typeof err === 'object' && err !== null) {
      const response = (err as { response?: { data?: { detail?: string; message?: string } } }).response
      const detail = response?.data?.detail || response?.data?.message
      if (detail) {
        error.value = detail
        return
      }
    }

    error.value = err instanceof Error && err.message ? err.message : '注册失败'
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
.password-label {
  display: flex;
  align-items: center;
  gap: 8px;
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
  margin: -8px 0 12px;
  padding: 12px 14px;
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  background: #eef2ff;
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
.password-tip {
  margin: -8px 0 16px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}
</style>
