<template>
  <div class="invite-page">
    <div class="invite-card">
      <div class="invite-icon">🤝</div>
      <div class="invite-title">团队邀请</div>

      <template v-if="loading">
        <div class="invite-description">正在读取邀请信息...</div>
      </template>

      <template v-else-if="!invitation">
        <div class="invite-description error">
          {{ statusMessage || '邀请链接不存在或已失效。' }}
        </div>
        <router-link class="invite-link-btn secondary" to="/">返回首页</router-link>
      </template>

      <template v-else>
        <div class="invite-team-name">{{ invitation.organization_nickname }}</div>
        <div class="invite-description">
          {{ invitation.inviter_name }} 邀请你加入团队，链接有效期至
          {{ formatFullDate(invitation.expires_at) }}。
        </div>

        <div class="invite-meta-list">
          <div class="invite-meta-item">
            <span>邀请人</span>
            <strong>{{ invitation.inviter_name }}</strong>
          </div>
          <div class="invite-meta-item">
            <span>团队类型</span>
            <strong>{{ invitation.organization_type }}</strong>
          </div>
          <div class="invite-meta-item">
            <span>当前状态</span>
            <strong :class="{ expired: expired }">{{ expired ? '已过期' : '可加入' }}</strong>
          </div>
        </div>

        <div v-if="statusMessage" class="invite-status" :class="inviteStatusType">
          {{ statusMessage }}
        </div>

        <template v-if="!userStore.isLogin">
          <div class="invite-description warning">请先登录或注册账号，再完成加入团队。</div>
          <div class="invite-actions stacked">
            <router-link class="invite-link-btn primary" :to="loginTarget">前往登录</router-link>
            <router-link class="invite-link-btn secondary" :to="registerTarget"
              >注册后加入</router-link
            >
          </div>
        </template>

        <template v-else>
          <div class="invite-description compact">当前账号：{{ userStore.user?.username }}</div>
          <div class="invite-actions">
            <button
              class="invite-link-btn primary"
              type="button"
              :disabled="expired || accepting"
              @click="acceptInvite"
            >
              {{ accepting ? '加入中...' : '接受邀请并加入团队' }}
            </button>
            <router-link class="invite-link-btn secondary" to="/app/project"
              >返回创建页</router-link
            >
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  acceptTeamInvitation,
  getInvitationByToken,
  isInvitationExpired,
  type TeamInvitationRecord,
} from '@/services/teamInvitations'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const accepting = ref(false)
const invitation = ref<TeamInvitationRecord | null>(null)
const statusMessage = ref('')
const inviteStatusType = ref<'success' | 'error' | 'warning'>('warning')

const token = computed(() => String(route.params.token || ''))
const expired = computed(() => (invitation.value ? isInvitationExpired(invitation.value) : false))
const redirectPath = computed(() => `/invite/${token.value}`)
const loginTarget = computed(() => ({ path: '/login', query: { redirect: redirectPath.value } }))
const registerTarget = computed(() => ({
  path: '/register',
  query: { redirect: redirectPath.value },
}))

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error !== null) {
    const maybeError = error as {
      response?: { data?: { detail?: string } }
      message?: string
    }
    return maybeError.response?.data?.detail || maybeError.message || fallback
  }
  return fallback
}

const loadInvitation = async () => {
  loading.value = true
  try {
    invitation.value = token.value ? await getInvitationByToken(token.value) : null
    if (!invitation.value) {
      statusMessage.value = '邀请链接不存在或已失效。'
      inviteStatusType.value = 'error'
      return
    }

    if (expired.value) {
      statusMessage.value = '该邀请链接已过期，请联系团队重新生成。'
      inviteStatusType.value = 'warning'
    } else {
      statusMessage.value = ''
    }
  } catch (error: unknown) {
    invitation.value = null
    statusMessage.value = getErrorMessage(error, '邀请链接不存在或已失效。')
    inviteStatusType.value = 'error'
  } finally {
    loading.value = false
  }
}

const acceptInvite = async () => {
  if (!userStore.user || !invitation.value || !token.value) return

  accepting.value = true
  try {
    const result = await acceptTeamInvitation(token.value, userStore.user)
    userStore.refreshUserOrganizations(result.user)
    userStore.setCurrentOrganization(result.organization.organization_nickname)
    statusMessage.value = result.alreadyJoined
      ? `你已在“${result.organization.organization_nickname}”团队中，无需重复加入。`
      : `已成功加入“${result.organization.organization_nickname}”，正在跳转到首页。`
    inviteStatusType.value = result.alreadyJoined ? 'warning' : 'success'
    await loadInvitation()
    window.setTimeout(() => {
      router.push('/app/guide')
    }, 600)
  } catch (error: unknown) {
    statusMessage.value = getErrorMessage(error, '加入团队失败，请稍后重试。')
    inviteStatusType.value = 'error'
  } finally {
    accepting.value = false
  }
}

const formatFullDate = (value: string) =>
  new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

onMounted(() => {
  loadInvitation()
})
</script>

<style scoped>
.invite-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
  padding: 24px;
}

.invite-card {
  width: min(94vw, 620px);
  background: #fff;
  border-radius: 28px;
  box-shadow: 0 28px 80px rgba(79, 70, 229, 0.16);
  padding: 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.invite-icon {
  width: 72px;
  height: 72px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  background: #eef2ff;
}

.invite-title {
  font-size: 30px;
  font-weight: 800;
  color: #0f172a;
}

.invite-team-name {
  font-size: 22px;
  font-weight: 700;
  color: #4338ca;
}

.invite-description {
  font-size: 15px;
  line-height: 1.7;
  color: #475569;
}

.invite-description.compact {
  margin-top: -4px;
}

.invite-description.warning {
  color: #9a3412;
}

.invite-description.error {
  color: #b91c1c;
}

.invite-meta-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.invite-meta-item {
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 14px 16px;
  background: #f8fafc;
}

.invite-meta-item span {
  display: block;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 8px;
}

.invite-meta-item strong {
  color: #0f172a;
  font-size: 15px;
}

.invite-meta-item .expired {
  color: #b91c1c;
}

.invite-status {
  border-radius: 16px;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 600;
}

.invite-status.success {
  background: #ecfdf5;
  color: #047857;
}

.invite-status.error {
  background: #fef2f2;
  color: #b91c1c;
}

.invite-status.warning {
  background: #fff7ed;
  color: #c2410c;
}

.invite-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.invite-actions.stacked {
  flex-direction: column;
}

.invite-link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  border-radius: 14px;
  padding: 0 18px;
  text-decoration: none;
  border: none;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}

.invite-link-btn.primary {
  background: linear-gradient(135deg, #4f46e5, #2563eb);
  color: #fff;
}

.invite-link-btn.secondary {
  background: #e2e8f0;
  color: #334155;
}

.invite-link-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 640px) {
  .invite-card {
    padding: 24px;
  }

  .invite-actions {
    flex-direction: column;
  }
}
</style>
