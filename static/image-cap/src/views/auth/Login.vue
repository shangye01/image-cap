<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>登录账号</h2>
      <form @submit.prevent="submit">
        <div>
          <label>用户名</label>
          <input v-model.trim="form.username" type="text" required />
        </div>

        <div>
          <label>密码</label>
          <input v-model="form.password" type="password" required />
        </div>

        <div>
          <label>验证码</label>
          <div class="captcha-row">
            <input
              v-model.trim="form.captcha_code"
              class="captcha-input"
              type="text"
              maxlength="10"
              placeholder="请输入图中内容"
              required
            />
            <button
              type="button"
              class="captcha-trigger"
              :disabled="captchaLoading"
              @click="refreshCaptcha()"
            >
              <img v-if="captchaImage" :src="captchaImage" alt="验证码" class="captcha-image" />
              <span v-else>{{ captchaLoading ? '加载中...' : '刷新验证码' }}</span>
            </button>
          </div>
          <p class="captcha-tip">看不清？点击图片刷新</p>
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" class="submit-btn" :disabled="loading || captchaLoading || !form.captcha_id">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="switch-link">
        还没有账号？
        <router-link :to="registerLink">去注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'AuthLogin' })
import { computed, onMounted, ref } from 'vue'
import { getCaptchaApi, loginApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const form = ref({
  username: '',
  password: '',
  captcha_id: '',
  captcha_code: '',
})

const loading = ref(false)
const captchaLoading = ref(false)
const captchaImage = ref('')
const error = ref('')
const redirectTarget = computed(() => String(route.query.redirect || '/app/guide'))
const registerLink = computed(() => ({
  path: '/register',
  query: route.query.redirect ? { redirect: redirectTarget.value } : {},
}))

const refreshCaptcha = async (preserveError = false) => {
  captchaLoading.value = true
  if (!preserveError) {
    error.value = ''
  }

  try {
    const result = await getCaptchaApi()
    form.value.captcha_id = result.captcha_id
    form.value.captcha_code = ''
    captchaImage.value = result.image_data
  } catch (err: unknown) {
    form.value.captcha_id = ''
    captchaImage.value = ''
    if (!preserveError) {
      error.value = getLoginErrorMessage(err) || '验证码加载失败，请稍后重试'
    }
  } finally {
    captchaLoading.value = false
  }
}

const getLoginErrorMessage = (err: unknown) => {
  if (typeof err === 'object' && err !== null) {
    const response = (err as { response?: { data?: { detail?: string; message?: string } } }).response
    const detail = response?.data?.detail || response?.data?.message
    if (detail) return detail
  }

  if (err instanceof Error && err.message) {
    return err.message
  }

  return '登录失败'
}

const submit = async () => {
  error.value = ''
  if (!form.value.captcha_id) {
    await refreshCaptcha()
    if (!form.value.captcha_id) {
      error.value = '验证码加载失败，请刷新后重试'
      return
    }
  }

  loading.value = true
  try {
    const result = await loginApi(form.value)
    store.login(result.user, result.access_token)
    router.push(redirectTarget.value)
  } catch (err: unknown) {
    error.value = getLoginErrorMessage(err)
    await refreshCaptcha(true)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void refreshCaptcha()
})
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
.captcha-row {
  display: flex;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 8px;
}
.captcha-input {
  flex: 1;
  margin-bottom: 0;
}
.captcha-trigger {
  width: 140px;
  padding: 0;
  border: 1px solid #d4d4d8;
  border-radius: 12px;
  background: #f8fafc;
  overflow: hidden;
}
.captcha-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.captcha-image {
  display: block;
  width: 100%;
  height: 48px;
  object-fit: cover;
}
.captcha-tip {
  margin: 0 0 16px;
  font-size: 12px;
  color: #64748b;
}
.submit-btn {
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
