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
              <el-avatar :size="92" :src="user.avatar">{{
                user.username?.slice(0, 1) || 'U'
              }}</el-avatar>
            </div>

            <h2 class="user-name">{{ user.username }}</h2>
            <div class="user-id">账号ID：{{ user.id }}</div>

            <div class="user-tags">
              <el-tag type="success" effect="light" round>{{
                user.is_active ? '当前活跃' : '离线'
              }}</el-tag>
              <el-tag effect="light" round>{{ primaryOrgType }}</el-tag>
            </div>

            <div class="user-meta">
              <div class="meta-item">
                <span class="meta-label">注册时间</span>
                <span class="meta-value">{{ user.created_at || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">最后登录</span>
                <span class="meta-value">{{ user.last_login_at || '-' }}</span>
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

              <div class="double-section">
                <div class="section-block section-half">
                  <div class="section-title">安全设置</div>

                  <div class="setting-list">
                    <!-- <div class="setting-item">
                      <div>
                        <div class="setting-name">修改密码</div>
                        <div class="setting-desc">定期更新密码可以有效提升账号安全性</div>
                      </div>
                      <el-button type="primary" plain @click="handleChangePassword">
                        去修改
                      </el-button>
                    </div> -->

                    <div class="setting-item">
                      <div>
                        <div class="setting-name">退出登录</div>
                        <div class="setting-desc">退出当前设备登录状态，重新访问需再次登录</div>
                      </div>
                      <el-button @click="handleLogout">退出</el-button>
                    </div>
                  </div>
                </div>

                <div class="section-block section-half">
                  <!-- <div class="section-title">快捷键说明</div>

                  <div class="shortcut-list">
                    <div class="shortcut-item" v-for="item in shortcutList" :key="item.label">
                      <span class="shortcut-label">{{ item.label }}</span>
                      <div class="shortcut-keys">
                        <span class="key-tag" v-for="key in item.keys" :key="key">{{ key }}</span>
                      </div>
                    </div>
                  </div> -->
                  <div class="section-title">组织概览</div>
                  <div class="shortcut-list">
                    <div class="shortcut-item">
                      <span class="shortcut-label">已加入组织数</span>
                      <div class="shortcut-keys">
                        <span class="key-tag">{{ teamList.length }}</span>
                      </div>
                    </div>
                    <div class="shortcut-item">
                      <span class="shortcut-label">默认组织</span>
                      <div class="shortcut-keys">
                        <span class="key-tag">{{ primaryOrganization }}</span>
                      </div>
                    </div>
                    <div class="shortcut-item">
                      <span class="shortcut-label">状态</span>
                      <div class="shortcut-keys">
                        <span class="key-tag">{{ user.is_active ? '活跃' : '离线' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
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
                  <el-table-column label="组织昵称" min-width="220">
                    <template #default="{ row }">
                      <div class="org-cell">
                        <div class="org-avatar">{{ row.organization_nickname.slice(0, 1) }}</div>
                        <div class="org-name">{{ row.organization_nickname }}</div>
                      </div>
                    </template>
                  </el-table-column>

                  <el-table-column label="组织类型" min-width="160">
                    <template #default="{ row }">
                      <el-tag :type="getOrgTypeTag(row.organization_type)" effect="light" round>{{
                        row.organization_type
                      }}</el-tag>
                    </template>
                  </el-table-column>

                  <el-table-column prop="joined_at" label="加入时间" min-width="180" />
                  <el-table-column prop="member_count" label="组织成员" min-width="120" />
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
  </div>
</template>

<script setup lang="js">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { logoutApi } from '@/api/auth'
import { getMyPerformanceSummary } from '@/api/performance'
import { useUserStore } from '@/stores/user'
import GradientBackground from '@/components/GradientBackground.vue'
const performanceSummary = ref(null)

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('profile')
const keyword = ref('')
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
const primaryOrganization = computed(() => teamList.value[0]?.organization_nickname || '-')
const primaryOrgType = computed(() => teamList.value[0]?.organization_type || '未加入组织')

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

const handleLogout = async () => {
  try {
    await logoutApi()
  } catch {
    // ignore
  } finally {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
const handleRefresh = () => {
  keyword.value = ''
  loadPerformanceSummary()
  ElMessage.success('已刷新组织信息')
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
  padding: 24px;
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
  gap: 20px;
}
.profile-sidebar,
.profile-main {
  min-width: 0;
}
.user-card,
.content-card {
  background: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.06);
}
.user-card__banner {
  height: 108px;
  background: linear-gradient(135deg, #818cf8, #38bdf8);
}
.user-card__content {
  padding: 0 24px 24px;
  margin-top: -46px;
}
.avatar-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.user-name {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}
.user-id {
  text-align: center;
  color: #64748b;
  margin-top: 6px;
}
.user-tags {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.user-meta {
  margin-top: 20px;
  display: grid;
  gap: 12px;
}
.meta-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}
.meta-label {
  color: #64748b;
}
.meta-value {
  color: #0f172a;
  text-align: right;
}
.content-card {
  padding: 24px;
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
  padding: 20px;
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
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.setting-name {
  font-weight: 600;
  color: #0f172a;
}
.setting-desc,
.table-subtitle {
  color: #64748b;
  font-size: 14px;
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
  width: 260px;
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
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
@media (max-width: 1024px) {
  .profile-layout {
    grid-template-columns: 1fr;
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
