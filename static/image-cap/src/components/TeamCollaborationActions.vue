<template>
  <div class="team-actions" ref="actionRootRef">
    <div class="switch-team-wrap">
      <button class="team-action-btn secondary" type="button" @click="toggleTeamMenu">
        <span>👥</span>
        <span>切换团队</span>
      </button>

      <transition name="menu-fade">
        <div v-if="teamMenuVisible" class="team-menu-dropdown">
          <div class="team-menu-title">我创建或加入的团队</div>

          <button
            v-for="organization in organizations"
            :key="organization.organization_nickname"
            class="team-menu-item"
            :class="{ active: organization.organization_nickname === activeOrganizationName }"
            type="button"
            @click="selectOrganization(organization.organization_nickname)"
          >
            <div class="team-menu-item-main">
              <span class="team-menu-name">{{ organization.organization_nickname }}</span>
              <span class="team-menu-type">{{ getOrganizationTypeLabel(organization) }}</span>
            </div>
            <span class="team-menu-meta">{{ organization.member_count || 1 }}人</span>
          </button>

          <div v-if="!organizations.length" class="team-empty">暂无可切换团队</div>
        </div>
      </transition>
    </div>

    <button
      class="team-action-btn secondary accent"
      type="button"
      :disabled="!currentOrganization || currentOrganization.organization_type !== '团队'"
      @click="openInviteDialog"
    >
      <span>✉️</span>
      <span>邀请成员</span>
    </button>

    <button
      class="team-action-btn primary"
      type="button"
      :disabled="!currentOrganization || !shareableProjects.length"
      @click="openShareDialog"
    >
      <span>🔗</span>
      <span>分享</span>
    </button>

    <teleport to="body">
      <transition name="dialog-fade">
        <div v-if="shareVisible" class="dialog-mask" @click="closeShareDialog">
          <div class="dialog-panel share-dialog-panel" @click.stop>
            <div class="share-dialog-header">
              <div>
                <div class="dialog-title">分享项目到团队</div>
                <div class="dialog-subtitle">
                  当前团队：{{ activeOrganizationName || '未选择团队' }}
                </div>
              </div>
              <button class="dialog-close-btn" type="button" @click="closeShareDialog">×</button>
            </div>

            <div class="dialog-body">
              <div class="share-project-card">
                <div class="share-project-label">选择分享项目</div>
                <select v-model="shareForm.projectId" class="share-project-select">
                  <option value="" disabled>请选择要分享的整个项目</option>
                  <option
                    v-for="project in shareableProjects"
                    :key="project.id"
                    :value="project.id"
                  >
                    {{ project.name }}
                  </option>
                </select>
                <div class="share-project-hint">分享后，成员会收到该项目的完整副本。</div>
              </div>

              <div class="share-member-header">选择团队成员</div>
              <div v-if="loadingMembers" class="team-empty team-empty-dialog">
                正在加载团队成员...
              </div>
              <div v-else-if="teamMembers.length" class="member-list">
                <label
                  v-for="member in teamMembers"
                  :key="member.id"
                  class="member-item"
                  :class="{ selected: shareForm.memberIds.includes(member.id) }"
                >
                  <input v-model="shareForm.memberIds" type="checkbox" :value="member.id" />
                  <div class="member-avatar">{{ member.name.slice(0, 1) }}</div>
                  <div class="member-content">
                    <div class="member-name">{{ member.name }}</div>
                    <div class="member-role">{{ member.role }}</div>
                  </div>
                </label>
              </div>
              <div v-else class="team-empty team-empty-dialog">当前团队暂无可分享成员</div>

              <textarea
                v-model.trim="shareForm.message"
                class="share-message"
                placeholder="补充一段分享说明（可选）"
              />
            </div>

            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="closeShareDialog">
                取消
              </button>
              <button
                class="dialog-btn primary"
                type="button"
                :disabled="shareSubmitting"
                @click="confirmShare"
              >
                {{ shareSubmitting ? '分享中...' : '确认分享' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <teleport to="body">
      <transition name="dialog-fade">
        <div v-if="inviteVisible" class="dialog-mask" @click="closeInviteDialog">
          <div class="dialog-panel invite-dialog-panel" @click.stop>
            <div class="share-dialog-header invite-dialog-header">
              <div>
                <div class="dialog-title">邀请成员加入团队</div>
                <div class="dialog-subtitle">
                  分享链接后，被邀请人登录并打开链接即可加入
                  {{ activeOrganizationName || '当前团队' }}
                </div>
              </div>
              <button class="dialog-close-btn" type="button" @click="closeInviteDialog">×</button>
            </div>

            <div class="dialog-body invite-dialog-body">
              <div class="invite-current-team">
                <span class="invite-badge">{{ activeOrganizationName || '未选择团队' }}</span>
                <span class="invite-tip">邀请链接 7 天内有效，可重复分享。</span>
              </div>

              <div class="invite-link-card">
                <div class="invite-link-label">团队邀请链接</div>
                <div class="invite-link-row">
                  <input
                    :value="inviteLoading ? '正在生成邀请链接...' : currentInviteLink"
                    class="invite-link-input"
                    readonly
                  />
                  <button
                    class="dialog-btn primary small"
                    type="button"
                    :disabled="inviteLoading || !currentInviteLink"
                    @click="copyInviteLink"
                  >
                    复制链接
                  </button>
                </div>
                <div class="invite-helper-text">
                  发送给成员后，对方进入链接并确认加入即可完成入队。
                </div>
              </div>

              <!-- <div class="invite-history-header">
                <span>最近生成的邀请</span>
                <button class="text-action" type="button" @click="generateInviteLink">
                  重新生成
                </button>
              </div> -->

              <!-- <div v-if="inviteHistory.length" class="invite-history-list">
                <div
                  v-for="invite in inviteHistory"
                  :key="invite.token"
                  class="invite-history-item"
                >
                  <div>
                    <div class="invite-history-time">{{ formatDateTime(invite.created_at) }}</div>
                    <div class="invite-history-meta">
                      已加入 {{ invite.accepted_user_ids.length }} 人 ·
                      {{ isInviteExpired(invite) ? '已过期' : '有效中' }}
                    </div>
                  </div>
                  <button
                    class="dialog-btn secondary small"
                    type="button"
                    @click="copyLink(invite.invite_link)"
                  >
                    复制
                  </button>
                </div>
              </div>
              <div v-else class="team-empty team-empty-dialog">暂未生成邀请链接</div> -->
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  createTeamInvitationApi,
  listOrganizationMembersApi,
  type TeamMember,
  type UserOrganization,
} from '@/api/auth'
import { shareProject } from '@/api/projectStorage'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  projectName: {
    type: String,
    default: '',
  },
  projectId: {
    type: String,
    default: '',
  },
  projectOptions: {
    type: Array as () => Array<{ id: string; name: string; isSharedCopy?: boolean }>,
    default: () => [],
  },
})

const userStore = useUserStore()
const actionRootRef = ref<HTMLElement | null>(null)
const teamMenuVisible = ref(false)
const shareVisible = ref(false)
const inviteVisible = ref(false)
const currentInviteLink = ref('')
const teamMembers = ref<TeamMember[]>([])
const loadingMembers = ref(false)
const inviteLoading = ref(false)
const shareSubmitting = ref(false)
const shareForm = reactive({
  projectId: '',
  memberIds: [] as string[],
  message: '',
})

const organizations = computed(() => userStore.user?.organizations || [])
const currentOrganization = computed(
  () => userStore.currentOrganization || organizations.value[0] || null
)
const activeOrganizationName = computed(
  () => currentOrganization.value?.organization_nickname || userStore.currentOrganizationName
)
const shareableProjects = computed(() =>
  (props.projectOptions || []).filter((project) => !project.isSharedCopy)
)
const selectedShareProject = computed(() => {
  if (!shareForm.projectId) return null
  return shareableProjects.value.find((project) => project.id === shareForm.projectId) || null
})

const toggleTeamMenu = () => {
  teamMenuVisible.value = !teamMenuVisible.value
}

const selectOrganization = (organizationName: string) => {
  userStore.setCurrentOrganization(organizationName)
  teamMenuVisible.value = false
}

const loadMembers = async () => {
  if (!activeOrganizationName.value) {
    teamMembers.value = []
    return
  }

  loadingMembers.value = true
  try {
    const response = await listOrganizationMembersApi(activeOrganizationName.value)
    const currentUserId = userStore.user?.id
    teamMembers.value = response.members.filter((member) => member.id !== currentUserId)
  } catch (error: any) {
    teamMembers.value = []
    window.alert(error?.response?.data?.detail || error?.message || '读取团队成员失败')
  } finally {
    loadingMembers.value = false
  }
}

const openShareDialog = async () => {
  if (!currentOrganization.value || !shareableProjects.value.length) return
  shareForm.projectId =
    shareableProjects.value.find((project) => project.id === props.projectId)?.id ||
    shareableProjects.value[0]?.id ||
    ''
  shareForm.memberIds = []
  shareForm.message = ''
  shareVisible.value = true
  await loadMembers()
}

const closeShareDialog = () => {
  shareVisible.value = false
}

const openInviteDialog = async () => {
  if (!currentOrganization.value || currentOrganization.value.organization_type !== '团队') return
  inviteVisible.value = true
  inviteLoading.value = true
  try {
    const invitation = await createTeamInvitationApi({
      organization_nickname: currentOrganization.value.organization_nickname,
    })
    currentInviteLink.value = `${window.location.origin}${invitation.invite_link}`
  } catch (error: any) {
    currentInviteLink.value = ''
    window.alert(error?.response?.data?.detail || error?.message || '生成邀请链接失败')
  } finally {
    inviteLoading.value = false
  }
}

const closeInviteDialog = () => {
  inviteVisible.value = false
}

const confirmShare = async () => {
  if (!currentOrganization.value || !shareForm.projectId) return
  if (!shareForm.memberIds.length) {
    window.alert('请至少选择一位团队成员')
    return
  }

  shareSubmitting.value = true
  try {
    const selectedMembers = teamMembers.value.filter((member) =>
      shareForm.memberIds.includes(member.id)
    )
    await shareProject(shareForm.projectId, {
      recipient_ids: [...shareForm.memberIds],
      organization_nickname: currentOrganization.value.organization_nickname,
      message: shareForm.message || undefined,
    })
    const sharedProjectName = selectedShareProject.value?.name || props.projectName || '当前项目'
    closeShareDialog()
    window.alert(
      `已将“${sharedProjectName}”分享给 ${selectedMembers.map((member) => member.name).join('、')}`
    )
  } catch (error: any) {
    window.alert(error?.response?.data?.detail || error?.message || '分享项目失败')
  } finally {
    shareSubmitting.value = false
  }
}

const copyLink = async (link: string) => {
  if (!link) return

  try {
    await navigator.clipboard.writeText(link)
    window.alert('邀请链接已复制，可直接发送给团队成员')
  } catch {
    window.prompt('复制失败，请手动复制以下链接', link)
  }
}

const copyInviteLink = async () => {
  if (!currentInviteLink.value) return

  await copyLink(currentInviteLink.value)
}

const getOrganizationTypeLabel = (organization: UserOrganization) =>
  organization.organization_type || '团队'

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (!actionRootRef.value?.contains(target)) {
    teamMenuVisible.value = false
  }
}

watch(activeOrganizationName, () => {
  if (shareVisible.value) {
    loadMembers()
  }
})

onMounted(() => {
  window.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.team-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  flex-wrap: wrap;
}

.switch-team-wrap {
  position: relative;
}

.team-action-btn {
  border: 1px solid #d7def0;
  border-radius: 12px;
  padding: 10px 16px;
  background: #fff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.team-action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.1);
}

.team-action-btn.primary {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(135deg, #4f46e5, #2563eb);
}

.team-action-btn.secondary {
  background: #fff;
}

.team-action-btn.secondary.accent {
  border-color: rgba(79, 70, 229, 0.22);
  color: #4338ca;
}

.team-action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.team-menu-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  width: 260px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
  padding: 12px;
  z-index: 30;
}

.team-menu-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}

.team-menu-item {
  width: 100%;
  border: none;
  border-radius: 12px;
  background: transparent;
  padding: 12px;
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.team-menu-item:hover,
.team-menu-item.active {
  background: #eef2ff;
}

.team-menu-item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.team-menu-name {
  font-weight: 700;
  color: #0f172a;
}

.team-menu-type,
.team-menu-meta,
.team-empty,
.dialog-subtitle,
.member-role,
.invite-helper-text,
.invite-history-meta,
.invite-tip {
  color: #64748b;
  font-size: 13px;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}

.dialog-panel {
  width: min(92vw, 640px);
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.24);
  overflow: hidden;
}

.share-dialog-panel,
.invite-dialog-panel {
  max-height: min(86vh, 760px);
  overflow: auto;
}

.share-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 24px 0;
}

.dialog-title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.dialog-close-btn {
  border: none;
  background: #f8fafc;
  color: #475569;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 22px;
}

.dialog-body {
  padding: 24px;
}

.share-project-card,
.invite-link-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 20px;
}

.share-project-label,
.invite-link-label,
.share-member-header,
.invite-history-header {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}

.share-project-name {
  margin-top: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.share-project-select {
  width: 100%;
  margin-top: 10px;
  border: 1px solid #d7def0;
  border-radius: 12px;
  padding: 11px 14px;
  font-size: 14px;
  color: #111827;
  background: #fff;
  outline: none;
}

.share-project-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.share-project-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #64748b;
}

.member-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.member-item {
  border: 1px solid #dbe3f3;
  border-radius: 16px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.member-item.selected {
  border-color: #4f46e5;
  background: #eef2ff;
}

.member-item input {
  margin: 0;
}

.member-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.member-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-name {
  font-weight: 700;
  color: #0f172a;
}

.share-message,
.invite-link-input {
  width: 100%;
  border: 1px solid #d7def0;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 14px;
  color: #1f2937;
  background: #fff;
}

.share-message {
  min-height: 96px;
  resize: vertical;
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 24px 24px;
}

.dialog-btn {
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #4f46e5, #2563eb);
  color: #fff;
}

.dialog-btn.secondary {
  background: #e2e8f0;
  color: #334155;
}

.dialog-btn.small {
  padding: 10px 14px;
  white-space: nowrap;
}

.team-empty-dialog {
  margin-top: 12px;
}

.invite-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.invite-current-team {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.invite-badge {
  display: inline-flex;
  align-items: center;
  background: #eef2ff;
  color: #4338ca;
  border-radius: 999px;
  padding: 8px 14px;
  font-weight: 700;
}

.invite-link-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
}

.invite-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.invite-history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.invite-history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px 16px;
}

.invite-history-time {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.text-action {
  border: none;
  background: transparent;
  color: #4f46e5;
  font-weight: 700;
  cursor: pointer;
}

.menu-fade-enter-active,
.menu-fade-leave-active,
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: all 0.2s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to,
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 768px) {
  .team-actions {
    width: 100%;
  }

  .team-action-btn,
  .switch-team-wrap {
    width: 100%;
  }

  .team-action-btn {
    justify-content: center;
  }

  .team-menu-dropdown,
  .dialog-panel {
    width: 100%;
  }

  .invite-link-row,
  .dialog-footer,
  .invite-history-item {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>