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
      class="team-action-btn primary"
      type="button"
      :disabled="!projectName || !currentOrganization"
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
                <div class="share-project-label">项目名称</div>
                <div class="share-project-name">{{ projectName || '请先进入项目后再分享' }}</div>
              </div>

              <div class="share-member-header">选择团队成员</div>
              <div v-if="teamMembers.length" class="member-list">
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
              <button class="dialog-btn primary" type="button" @click="confirmShare">
                确认分享
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  projectName: {
    type: String,
    default: '',
  },
})

const TEAM_MEMBER_STORAGE_KEY = 'team_member_map'
const PROJECT_SHARE_STORAGE_KEY = 'project_share_history'

const userStore = useUserStore()
const actionRootRef = ref(null)
const teamMenuVisible = ref(false)
const shareVisible = ref(false)
const shareForm = reactive({
  memberIds: [],
  message: '',
})

const organizations = computed(() => userStore.user?.organizations || [])
const currentOrganization = computed(() => {
  const storeOrganization = userStore.currentOrganization
  if (storeOrganization && storeOrganization.organization_type !== '个人') return storeOrganization
  return organizations.value[0] || null
})
const activeOrganizationName = computed(
  () => currentOrganization.value?.organization_nickname || userStore.currentOrganizationName
)

const teamMembers = computed(() => {
  if (!currentOrganization.value) return []

  const memberMap = readMemberMap()
  const existing = memberMap[currentOrganization.value.organization_nickname]
  if (existing?.length) return existing

  const generatedMembers = buildDefaultMembers(currentOrganization.value)
  memberMap[currentOrganization.value.organization_nickname] = generatedMembers
  localStorage.setItem(TEAM_MEMBER_STORAGE_KEY, JSON.stringify(memberMap))
  return generatedMembers
})

const toggleTeamMenu = () => {
  teamMenuVisible.value = !teamMenuVisible.value
}

const selectOrganization = (organizationName) => {
  userStore.setCurrentOrganization(organizationName)
  teamMenuVisible.value = false
}

const openShareDialog = () => {
  if (!props.projectName || !currentOrganization.value) return
  shareForm.memberIds = []
  shareForm.message = ''
  shareVisible.value = true
}

const closeShareDialog = () => {
  shareVisible.value = false
}

const confirmShare = () => {
  if (!shareForm.memberIds.length) {
    window.alert('请至少选择一位团队成员')
    return
  }

  const history = JSON.parse(localStorage.getItem(PROJECT_SHARE_STORAGE_KEY) || '[]')
  const selectedMembers = teamMembers.value.filter((member) =>
    shareForm.memberIds.includes(member.id)
  )

  history.unshift({
    id: `${Date.now()}`,
    projectName: props.projectName,
    organizationName: activeOrganizationName.value,
    memberIds: [...shareForm.memberIds],
    memberNames: selectedMembers.map((member) => member.name),
    message: shareForm.message,
    sharedAt: new Date().toISOString(),
  })

  localStorage.setItem(PROJECT_SHARE_STORAGE_KEY, JSON.stringify(history))
  closeShareDialog()
  window.alert(
    `已将“${props.projectName}”分享给 ${selectedMembers.map((member) => member.name).join('、')}`
  )
}

const getOrganizationTypeLabel = (organization) => organization.organization_type || '团队'

const readMemberMap = () => {
  try {
    return JSON.parse(localStorage.getItem(TEAM_MEMBER_STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

const buildDefaultMembers = (organization) => {
  const count = Math.max(organization.member_count || 1, 1)
  return Array.from({ length: count }, (_, index) => ({
    id: `${organization.organization_nickname}-${index + 1}`,
    name:
      index === 0
        ? `${organization.organization_nickname}负责人`
        : `${organization.organization_nickname}成员${index + 1}`,
    role: index === 0 ? '管理员' : '团队成员',
  }))
}

const handleClickOutside = (event) => {
  if (!actionRootRef.value?.contains(event.target)) {
    teamMenuVisible.value = false
  }
}

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
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.1);
}

.team-action-btn.primary {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(135deg, #5b8def, #7359f8);
}

.team-action-btn.secondary {
  background: rgba(255, 255, 255, 0.95);
}

.team-action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.team-menu-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 10px);
  width: 300px;
  background: #fff;
  border: 1px solid #e6ebf5;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.12);
  z-index: 30;
}

.team-menu-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
}

.team-menu-item {
  width: 100%;
  border: none;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  margin-bottom: 8px;
}

.team-menu-item.active {
  background: #eef4ff;
  color: #3157c9;
}

.team-menu-item-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.team-menu-name {
  font-size: 14px;
  font-weight: 600;
}

.team-menu-type,
.team-menu-meta,
.dialog-subtitle {
  font-size: 12px;
  color: #64748b;
}

.team-empty {
  padding: 18px 12px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 80;
}

.dialog-panel {
  width: min(560px, 100%);
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.2);
}

.share-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-close-btn {
  border: none;
  background: transparent;
  font-size: 28px;
  color: #94a3b8;
  cursor: pointer;
}

.share-project-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  margin-bottom: 18px;
}

.share-project-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.share-project-name,
.share-member-header {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.share-member-header {
  margin-bottom: 12px;
}

.member-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.member-item {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.member-item.selected {
  border-color: #5b8def;
  background: #eef4ff;
}

.member-item input {
  margin: 0;
}

.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b8def, #7359f8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.member-content {
  min-width: 0;
}

.member-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.member-role {
  font-size: 12px;
  color: #64748b;
}

.team-empty-dialog {
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 14px;
}

.share-message {
  width: 100%;
  min-height: 96px;
  border-radius: 14px;
  border: 1px solid #d7def0;
  padding: 12px 14px;
  font-size: 14px;
  resize: vertical;
  margin-top: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.dialog-btn {
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.dialog-btn.secondary {
  background: #eef2f7;
  color: #475569;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #5b8def, #7359f8);
  color: #fff;
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
    flex-wrap: wrap;
  }

  .switch-team-wrap,
  .team-action-btn {
    width: 100%;
  }

  .member-list {
    grid-template-columns: 1fr;
  }

  .team-menu-dropdown {
    width: min(320px, calc(100vw - 32px));
  }
}
</style>