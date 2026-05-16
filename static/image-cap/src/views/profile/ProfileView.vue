<template>
  <div class="profile-page">
     <GradientBackground />
    <div class="profile-header">
      <div>
        <h1 class="page-title">个人中心</h1>
        <p class="page-desc">管理个人资料、账号安全与团队信息</p>
      </div>
    </div>

    <div class="profile-layout">
      <!-- 左侧用户卡片 -->
      <div class="profile-sidebar">
        <div class="user-card">
          <div class="user-card__banner"></div>

          <div class="user-card__content">
            <div class="avatar-wrapper">
              <el-avatar :size="80" :src="user.avatar">{{
                user.username?.slice(0, 1) || 'U'
              }}</el-avatar>
            </div>

            <div class="user-name-row">
              <h2 class="user-name">{{ user.username }}</h2>
              <button type="button" class="user-name-edit" @click="openUsernameDialog">
                <el-icon><EditPen /></el-icon>
              </button>
            </div>
            <div class="user-id">账号ID：{{ user.id }}</div>

            <div class="user-tags">
              <el-tag type="success" effect="light" round>{{
                user.is_active ? '当前活跃' : '离线'
              }}</el-tag>
              <el-tag effect="light" round>{{ primaryOrgType }}</el-tag>
            </div>

            <div class="sidebar-action-list">
              <div class="setting-item">
                <div>
                  <div class="setting-name">修改密码</div>
                  <div class="setting-desc">更新登录密码以提升账号安全性</div>
                </div>
                <el-button @click="openPasswordDialog">修改</el-button>
              </div>
              <div class="setting-item">
                <div>
                  <div class="setting-name">注销账户</div>
                  <div class="setting-desc">永久删除当前账号及其登录状态</div>
                </div>
                <el-button type="danger" plain @click="handleDeleteAccount">注销</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧内容 -->
      <div class="profile-main">
        <div class="content-card">
          <!-- 自定义 tabs -->
          <div class="custom-tabs">
            <div
              class="custom-tab"
              :class="{ active: activeTab === 'profile' }"
              @click="activeTab = 'profile'"
            >
              个人信息
            </div>
            <div
              class="custom-tab"
              :class="{ active: activeTab === 'teams' }"
              @click="activeTab = 'teams'"
            >
              加入的团队
            </div>
          </div>

          <transition name="fade-slide" mode="out-in">
            <!-- 个人信息 -->
            <div v-if="activeTab === 'profile'" key="profile" class="panel-wrapper">
              <div class="section-block">
                <div class="section-title">基础信息</div>
                <div class="info-grid">
                  <div class="info-item">
                    <div class="info-label">用户名称</div>
                    <div class="info-value">{{ user.username }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">账号ID</div>
                    <div class="info-value">{{ user.id }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">注册时间</div>
                    <div class="info-value">{{ user.created_at || '-' }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">最后登录时间</div>
                    <div class="info-value">{{ user.last_login_at || '-' }}</div>
                  </div>
                </div>
              </div>

              <div class="section-block profile-score-section">
                <div class="section-title">评分概览</div>
                <div v-if="performanceSummary" class="score-grid">
                  <div class="score-card score-card--primary">
                    <div class="score-card__label">综合评分</div>
                    <div class="score-card__value">{{ performanceSummary.scores.total }}</div>
                    <div class="score-card__meta">
                      等级 {{ performanceSummary.level }} · 最近 {{ performanceSummary.period_days }} 天
                    </div>
                  </div>
                  <div class="score-card">
                    <div class="score-card__label">准确率</div>
                    <div class="score-card__value">{{ performanceSummary.scores.accuracy }}</div>
                    <div class="score-card__meta">
                      审核覆盖 {{ performanceSummary.mvp.review_coverage }}%
                    </div>
                  </div>
                  <div class="score-card">
                    <div class="score-card__label">效率分</div>
                    <div class="score-card__value">{{ performanceSummary.scores.speed }}</div>
                    <div class="score-card__meta">
                      平均 {{ performanceSummary.mvp.avg_task_minutes }} 分钟/任务
                    </div>
                  </div>
                  <div class="score-card">
                    <div class="score-card__label">协作质量</div>
                    <div class="score-card__value">{{ performanceSummary.scores.collaboration }}</div>
                    <div class="score-card__meta">
                      稳定性 {{ performanceSummary.scores.stability }}
                    </div>
                  </div>
                </div>
                <el-empty
                  v-else
                  description="暂无评分数据，完成标注并经过审核后会逐步生成"
                  :image-size="72"
                />
              </div>
            </div>

            <!-- 团队信息 -->
            <div v-else key="teams" class="panel-wrapper">
              <div class="section-block">
                <div class="table-header">
                  <div>
                    <div class="section-title mb-4">我加入的团队</div>
                    <div class="table-subtitle">共 {{ filteredTeamList.length }} 个组织</div>
                  </div>

                  <div class="table-tools">
                    <el-input
                      v-model="keyword"
                      placeholder="搜索组织昵称"
                      clearable
                      class="search-input"
                    >
                      <template #prefix
                        ><el-icon><Search /></el-icon
                      ></template>
                    </el-input>

                    <el-button @click="handleRefresh"
                      ><el-icon><Refresh /></el-icon
                    ></el-button>
                  </div>
                </div>

                <el-table :data="filteredTeamList" class="team-table" stripe style="width: 100%">
                  <el-table-column label="组织昵称" min-width="190">
                    <template #default="{ row }">
                      <div class="org-cell">
                        <div class="org-avatar">{{ row.organization_nickname.slice(0, 1) }}</div>
                        <div class="org-name">{{ row.organization_nickname }}</div>
                      </div>
                    </template>
                  </el-table-column>

                  <el-table-column label="组织类型" min-width="130">
                    <template #default="{ row }">
                      <el-tag :type="getOrgTypeTag(row.organization_type)" effect="light" round>{{
                        row.organization_type
                      }}</el-tag>
                    </template>
                  </el-table-column>

                  <el-table-column prop="joined_at" label="加入时间" min-width="150" />
                  <el-table-column prop="member_count" label="组织成员" min-width="100" />
                  <el-table-column label="操作" min-width="96">
                    <template #default="{ row }">
                      <el-button
                        v-if="row.organization_type === '团队'"
                        type="danger"
                        link
                        :loading="leavingOrganizationName === row.organization_nickname"
                        @click="handleLeaveOrganization(row)"
                      >
                        退出团队
                      </el-button>
                      <span v-else class="table-action-placeholder">-</span>
                    </template>
                  </el-table-column>
                </el-table>

                <el-empty
                  v-if="filteredTeamList.length === 0"
                  description="暂无匹配的团队信息"
                  :image-size="90"
                />
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <el-dialog v-model="usernameDialogVisible" title="修改用户名" width="420px" @closed="resetUsernameForm">
      <el-form label-position="top">
        <el-form-item label="新用户名">
          <el-input v-model.trim="usernameForm.username" maxlength="50" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="usernameDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="usernameSubmitting" @click="submitUsernameChange">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="460px" @closed="resetPasswordForm">
      <el-form label-position="top">
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.currentPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
          <div class="password-policy-tip">{{ PASSWORD_POLICY_HINT }}</div>
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="submitPasswordChange">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="js">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Search, Refresh } from '@element-plus/icons-vue'
import {
  changePasswordApi,
  deleteAccountApi,
  leaveOrganizationApi,
  updateUsernameApi,
} from '@/api/auth'
import { getMyPerformanceSummary } from '@/api/performance'
import { useUserStore } from '@/stores/user'
import { PASSWORD_POLICY_HINT, validatePasswordPolicy } from '@/utils/passwordPolicy'
import GradientBackground from '@/components/GradientBackground.vue'
const performanceSummary = ref(null)

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('profile')
const keyword = ref('')
const usernameDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const usernameSubmitting = ref(false)
const passwordSubmitting = ref(false)
const leavingOrganizationName = ref('')
const usernameForm = reactive({
  username: '',
})
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
// const performanceSummary = ref<PerformanceSummary | null>(null)

const user = computed(
  () =>
    userStore.user || {
      id: '-',
      username: '未登录',
      avatar: '',
      is_active: false,
      created_at: '-',
      last_login_at: '-',
      organizations: [],
    }
)

const teamList = computed(() => user.value.organizations || [])

const filteredTeamList = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return teamList.value
  return teamList.value.filter((item) => item.organization_nickname.toLowerCase().includes(value))
})
const primaryOrgType = computed(() => teamList.value[0]?.organization_type || '未加入组织')

const getErrorMessage = (error, fallback) => error?.response?.data?.detail || error?.message || fallback

const loadPerformanceSummary = async () => {
  if (!userStore.isLogin) {
    performanceSummary.value = null
    return
  }

  try {
    const response = await getMyPerformanceSummary()
    performanceSummary.value = response?.summary?.has_data ? response.summary : null
  } catch (error) {
    console.error('加载评分摘要失败:', error)
    performanceSummary.value = null
  }
}

const openUsernameDialog = () => {
  usernameForm.username = user.value.username || ''
  usernameDialogVisible.value = true
}

const resetUsernameForm = () => {
  usernameForm.username = user.value.username || ''
  usernameSubmitting.value = false
}

const submitUsernameChange = async () => {
  const username = usernameForm.username.trim()
  if (username.length < 2) {
    ElMessage.warning('用户名至少 2 个字符')
    return
  }

  usernameSubmitting.value = true
  try {
    const response = await updateUsernameApi({ username })
    userStore.setUser(response.user)
    ElMessage.success(response.message || '用户名已更新')
    usernameDialogVisible.value = false
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '修改用户名失败'))
  } finally {
    usernameSubmitting.value = false
  }
}

const openPasswordDialog = () => {
  resetPasswordForm()
  passwordDialogVisible.value = true
}

const resetPasswordForm = () => {
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  passwordSubmitting.value = false
}

const submitPasswordChange = async () => {
  if (!passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
    ElMessage.warning('请填写完整密码信息')
    return
  }
  const passwordError = validatePasswordPolicy(passwordForm.newPassword)
  if (passwordError) {
    ElMessage.warning(passwordError)
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  passwordSubmitting.value = true
  try {
    const response = await changePasswordApi({
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
    })
    ElMessage.success(response.message || '密码已更新')
    passwordDialogVisible.value = false
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '修改密码失败'))
  } finally {
    passwordSubmitting.value = false
  }
}

const handleDeleteAccount = async () => {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入当前密码以确认注销账户。注销后账号将被永久删除。',
      '注销账户',
      {
        confirmButtonText: '确认注销',
        cancelButtonText: '取消',
        inputType: 'password',
        inputPlaceholder: '请输入当前密码',
        inputValidator: (input) => (input && input.trim().length >= 6 ? true : '请输入正确的当前密码'),
      },
    )

    const response = await deleteAccountApi({ password: value.trim() })
    userStore.logout()
    ElMessage.success(response.message || '账户已注销')
    router.push('/login')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '注销账户失败'))
  }
}

const handleRefresh = () => {
  keyword.value = ''
  loadPerformanceSummary()
  ElMessage.success('已刷新组织信息')
}

const handleLeaveOrganization = async (organization) => {
  try {
    await ElMessageBox.confirm(
      `确认退出团队“${organization.organization_nickname}”吗？退出后将失去该团队下的协作权限。`,
      '退出团队',
      {
        confirmButtonText: '确认退出',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }

  leavingOrganizationName.value = organization.organization_nickname
  try {
    const response = await leaveOrganizationApi(organization.organization_nickname)
    userStore.setUser(response.user)
    ElMessage.success(response.message || '已退出团队')
    if (keyword.value.trim()) {
      keyword.value = ''
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '退出团队失败'))
  } finally {
    leavingOrganizationName.value = ''
  }
}

const getOrgTypeTag = (type) => {
  if (type === '团队') return 'primary'
  return ''
}

onMounted(() => {
  loadPerformanceSummary()
})
</script>

<style scoped>
.profile-page {
  padding: 20px 16px 20px 14px;
  overflow-x: hidden;
}
.profile-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}
.page-desc {
  margin-top: 8px;
  color: #64748b;
}
.profile-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 14px;
}
.profile-sidebar,
.profile-main {
  min-width: 0;
}
.profile-main {
  display: flex;
  justify-content: flex-start;
  overflow: hidden;
}
.user-card,
.content-card {
  background: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.06);
}
.user-card__banner {
  height: 88px;
  background: linear-gradient(135deg, #818cf8, #38bdf8);
}
.user-card__content {
  padding: 0 20px 18px;
  margin-top: -36px;
}
.avatar-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}
.user-name {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}
.user-name-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.user-name-edit {
  width: 30px;
  height: 30px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.user-name-edit:hover {
  color: #2563eb;
  border-color: rgba(37, 99, 235, 0.28);
  background: #eff6ff;
}
.user-id {
  text-align: center;
  color: #64748b;
  margin-top: 4px;
  font-size: 13px;
}
.user-tags {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.sidebar-action-list {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}
.content-card {
  width: calc(100% - 20px);
  max-width: 100%;
  box-sizing: border-box;
  padding: 18px;
}
.custom-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.custom-tab {
  padding: 10px 16px;
  border-radius: 12px;
  background: #f1f5f9;
  cursor: pointer;
  color: #475569;
}
.custom-tab.active {
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}
.section-block {
  background: #f8fafc;
  border-radius: 20px;
  padding: 18px;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 18px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.info-item {
  padding: 16px;
  border-radius: 16px;
  background: #fff;
}
.info-label {
  color: #64748b;
  margin-bottom: 8px;
}
.info-value {
  color: #0f172a;
  font-weight: 600;
  word-break: break-all;
}
.profile-score-section {
  margin-top: 20px;
}
.score-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}
.score-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}
.score-card--primary {
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
  border-color: #bfdbfe;
}
.score-card__label {
  color: #64748b;
  font-size: 13px;
}
.score-card__value {
  margin-top: 10px;
  font-size: 30px;
  line-height: 1;
  font-weight: 700;
  color: #0f172a;
}
.score-card__meta {
  margin-top: 10px;
  color: #475569;
  font-size: 13px;
}
.double-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-top: 20px;
}
.setting-list,
.shortcut-list {
  display: grid;
  gap: 14px;
}
.setting-item,
.shortcut-item {
  background: #fff;
  border-radius: 16px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.setting-name {
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
}
.setting-desc,
.table-subtitle {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}
.shortcut-label {
  color: #0f172a;
  font-weight: 600;
}
.shortcut-keys {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.key-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: #e0e7ff;
  color: #4338ca;
  font-size: 13px;
}
.table-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}
.table-tools {
  display: flex;
  gap: 10px;
  align-items: center;
}
.search-input {
  width: 200px;
}
.org-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.org-avatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #c7d2fe;
  color: #3730a3;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.org-name {
  font-weight: 600;
  color: #0f172a;
}
.table-action-placeholder {
  color: #94a3b8;
}
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
.password-policy-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}
@media (max-width: 1024px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
  .content-card {
    width: 100%;
  }
  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .double-section {
    grid-template-columns: 1fr;
  }
  .table-header {
    flex-direction: column;
    align-items: stretch;
  }
  .search-input {
    width: 100%;
  }
}
@media (max-width: 640px) {
  .score-grid {
    grid-template-columns: 1fr;
  }
}
/* 关键：内容层必须在背景之上 */
.content-wrapper {
  position: relative;
  z-index: 1;  /* 确保内容在背景装饰之上 */
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}
</style>
