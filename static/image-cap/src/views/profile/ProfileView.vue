<template>
  <div class="profile-page">
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
              <el-avatar :size="92" :src="user.avatar">
                {{ user.accountName?.slice(0, 1) || 'U' }}
              </el-avatar>
              <div class="avatar-edit">
                <el-icon><Camera /></el-icon>
              </div>
            </div>

            <h2 class="user-name">{{ user.accountName }}</h2>
            <div class="user-nickname">@{{ user.communityName }}</div>

            <div class="user-id">账号ID：{{ user.accountId }}</div>

            <div class="user-tags">
              <el-tag type="primary" effect="light" round>已认证用户</el-tag>
              <el-tag effect="light" round>普通成员</el-tag>
            </div>

            <div class="user-meta">
              <div class="meta-item">
                <span class="meta-label">注册时间</span>
                <span class="meta-value">{{ user.registerTime }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">最后登录</span>
                <span class="meta-value">{{ user.lastLoginTime }}</span>
              </div>
            </div>

            <!-- <div class="user-actions">
              <el-button type="primary" plain class="action-btn" @click="handleChangePassword">
                修改密码
              </el-button>
              <el-button class="action-btn danger-btn" @click="handleLogout"> 退出登录 </el-button>
            </div> -->
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
                    <div class="info-label">账号名称</div>
                    <div class="info-value">{{ user.accountName }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">账号ID</div>
                    <div class="info-value">{{ user.accountId }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">社区昵称</div>
                    <div class="info-value">{{ user.communityName }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">注册时间</div>
                    <div class="info-value">{{ user.registerTime }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">最后登录时间</div>
                    <div class="info-value">{{ user.lastLoginTime }}</div>
                  </div>
                </div>
              </div>

              <div class="double-section">
                <div class="section-block section-half">
                  <div class="section-title">安全设置</div>

                  <div class="setting-list">
                    <div class="setting-item">
                      <div>
                        <div class="setting-name">修改密码</div>
                        <div class="setting-desc">定期更新密码可以有效提升账号安全性</div>
                      </div>
                      <el-button type="primary" plain @click="handleChangePassword">
                        去修改
                      </el-button>
                    </div>

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
                  <div class="section-title">快捷键说明</div>

                  <div class="shortcut-list">
                    <div class="shortcut-item" v-for="item in shortcutList" :key="item.label">
                      <span class="shortcut-label">{{ item.label }}</span>
                      <div class="shortcut-keys">
                        <span class="key-tag" v-for="key in item.keys" :key="key">{{ key }}</span>
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
                    <div class="table-subtitle">共 {{ teamList.length }} 个组织</div>
                  </div>

                  <div class="table-tools">
                    <el-input
                      v-model="keyword"
                      placeholder="搜索组织昵称"
                      clearable
                      class="search-input"
                    >
                      <template #prefix>
                        <el-icon><Search /></el-icon>
                      </template>
                    </el-input>

                    <el-button @click="handleRefresh">
                      <el-icon><Refresh /></el-icon>
                    </el-button>
                  </div>
                </div>

                <el-table :data="filteredTeamList" class="team-table" stripe style="width: 100%">
                  <el-table-column label="组织昵称" min-width="220">
                    <template #default="{ row }">
                      <div class="org-cell">
                        <div class="org-avatar">{{ row.orgName.slice(0, 1) }}</div>
                        <div class="org-name">{{ row.orgName }}</div>
                      </div>
                    </template>
                  </el-table-column>

                  <el-table-column label="组织类型" min-width="160">
                    <template #default="{ row }">
                      <el-tag :type="getOrgTypeTag(row.orgType)" effect="light" round>
                        {{ row.orgType }}
                      </el-tag>
                    </template>
                  </el-table-column>

                  <el-table-column prop="joinTime" label="加入时间" min-width="180" />
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

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Camera, Search, Refresh } from '@element-plus/icons-vue'

const activeTab = ref('profile')
const keyword = ref('')

const user = ref({
  avatar: 'https://picsum.photos/120/120',
  accountName: '郑野',
  accountId: 'U20260319001',
  communityName: '夜行开发者',
  registerTime: '2025-06-12 14:33:21',
  lastLoginTime: '2026-03-19 09:24:17',
})

const shortcutList = ref([
  { label: '删除选中标注', keys: ['Delete'] },
  { label: '修改标签', keys: ['F2'] },
  { label: '清除所有标注', keys: ['Ctrl', 'Delete'] },
  { label: '取消选择', keys: ['Esc'] },
  { label: '全屏模式', keys: ['F11'] },
])

const teamList = ref([
  {
    orgName: '星海社区',
    orgType: '个人',
    joinTime: '2025-07-03 10:22:11',
  },
  {
    orgName: '未来产品组',
    orgType: '团队',
    joinTime: '2025-08-15 09:16:38',
  },
  {
    orgName: '云启科技',
    orgType: '团队',
    joinTime: '2025-09-21 18:03:47',
  },
  {
    orgName: '前端共创联盟',
    orgType: '团队',
    joinTime: '2025-11-08 13:45:02',
  },
])

const filteredTeamList = computed(() => {
  const val = keyword.value.trim().toLowerCase()
  if (!val) return teamList.value
  return teamList.value.filter((item) => item.orgName.toLowerCase().includes(val))
})

function getOrgTypeTag(type) {
  const map = {
    企业组织: 'primary',
    社区组织: 'success',
    项目组: 'warning',
  }
  return map[type] || ''
}

function handleChangePassword() {
  ElMessage.success('跳转到修改密码页面')
}

function handleRefresh() {
  ElMessage.success('团队列表已刷新')
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('退出后需要重新登录才能继续访问系统，确认退出吗？', '确认退出登录', {
      confirmButtonText: '确认退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    ElMessage.success('已退出登录')
  } catch (error) {
    // 用户取消
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100%;
  padding: 24px;
  background: radial-gradient(circle at top left, rgba(79, 124, 255, 0.08), transparent 24%),
    radial-gradient(circle at top right, rgba(109, 211, 251, 0.1), transparent 20%), #f5f7fb;
  box-sizing: border-box;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}

.page-desc {
  margin: 8px 0 0;
  font-size: 14px;
  color: #6b7280;
}

.profile-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 24px;
  align-items: start;
}

.profile-sidebar,
.profile-main {
  min-width: 0;
}

.user-card,
.content-card,
.section-block {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(31, 41, 55, 0.08);
}

.user-card {
  overflow: hidden;
  position: sticky;
  top: 24px;
}

.user-card__banner {
  height: 120px;
  background: linear-gradient(135deg, #4f7cff 0%, #6dd3fb 100%);
}

.user-card__content {
  position: relative;
  padding: 0 22px 24px;
  margin-top: -46px;
  text-align: center;
}

.avatar-wrapper {
  position: relative;
  width: fit-content;
  margin: 0 auto;
}

.avatar-wrapper :deep(.el-avatar) {
  border: 4px solid #ffffff;
  box-shadow: 0 8px 18px rgba(79, 124, 255, 0.25);
}

.avatar-edit {
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #4f7cff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 14px rgba(79, 124, 255, 0.35);
  cursor: pointer;
}

.user-name {
  margin: 16px 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.user-nickname {
  font-size: 14px;
  color: #4f7cff;
  margin-bottom: 10px;
}

.user-id {
  display: inline-block;
  padding: 6px 12px;
  font-size: 13px;
  color: #6b7280;
  background: #f3f6ff;
  border-radius: 999px;
}

.user-tags {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.user-meta {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #eef2f7;
}

.meta-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  padding: 8px 0;
}

.meta-label {
  color: #6b7280;
}

.meta-value {
  color: #1f2937;
  text-align: right;
}

.user-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-top: 22px;
}

.action-btn {
  width: 100%;
  height: 42px;
  border-radius: 12px;
}

.danger-btn {
  color: #ef4444;
  border-color: #fecaca;
  background: #fff5f5;
}

.content-card {
  padding: 20px;
  min-height: 640px;
}

.custom-tabs {
  display: inline-flex;
  padding: 6px;
  background: #f3f6fb;
  border-radius: 14px;
  margin-bottom: 22px;
}

.custom-tab {
  min-width: 108px;
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.custom-tab.active {
  background: #ffffff;
  color: #4f7cff;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(31, 41, 55, 0.08);
}

.panel-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-block {
  padding: 22px;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.06);
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 18px;
}

.mb-4 {
  margin-bottom: 4px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.info-item {
  padding: 18px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfcff 0%, #f7f9fd 100%);
  border: 1px solid #edf1f7;
  transition: all 0.25s ease;
}

.info-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(79, 124, 255, 0.08);
}

.info-label {
  font-size: 13px;
  color: #8a94a6;
  margin-bottom: 10px;
}

.info-value {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  word-break: break-all;
}

.double-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.setting-list,
.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.setting-item,
.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 14px;
  background: #f9fbff;
  border: 1px solid #edf1f7;
}

.setting-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.setting-desc {
  font-size: 13px;
  color: #7b8794;
}

.shortcut-label {
  font-size: 14px;
  color: #374151;
}

.shortcut-keys {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.key-tag {
  min-width: 34px;
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #d9e0ea;
  color: #1f2937;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.03);
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.table-subtitle {
  font-size: 13px;
  color: #8a94a6;
}

.table-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 240px;
}

.team-table {
  --el-table-border-color: #eef2f7;
  --el-table-header-bg-color: #f7faff;
  --el-table-row-hover-bg-color: #f8fbff;
  border-radius: 14px;
  overflow: hidden;
}

.org-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.org-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4f7cff 0%, #6dd3fb 100%);
  color: #ffffff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.org-name {
  font-weight: 600;
  color: #1f2937;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.28s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 1200px) {
  .info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 992px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }

  .user-card {
    position: static;
  }

  .double-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .profile-page {
    padding: 16px;
  }

  .content-card,
  .section-block {
    padding: 16px;
    border-radius: 16px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .table-header {
    flex-direction: column;
    align-items: stretch;
  }

  .table-tools {
    justify-content: space-between;
  }

  .search-input {
    width: 100%;
  }

  .shortcut-item,
  .setting-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>