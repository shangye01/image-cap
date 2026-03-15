<template>
  <div class="history-page">
    <header class="top-nav">
      <nav class="nav-list">
        <button
          v-for="item in navItems"
          :key="item"
          class="nav-item"
          :class="{ active: activeNav === item }"
          type="button"
          @click="activeNav = item"
        >
          {{ item }}
        </button>
      </nav>

      <div class="header-actions">
        <button class="invite-btn" type="button">邀请成员</button>
        <button class="add-btn" type="button" @click="$router.push('/app/publish')">＋ 添加</button>
      </div>
    </header>

    <section class="toolbar">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          class="tab"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab === '全部' ? `全部 (${projectList.length})` : tab }}
        </button>
      </div>

      <div class="filters">
        <button v-for="filter in filters" :key="filter" class="filter-btn">
          {{ filter }} <span class="arrow">⌄</span>
        </button>
        <button class="icon-btn" @click="toggleSort" title="切换排序">↕</button>
      </div>
    </section>

    <main class="content-area">
      <div v-if="projectList.length > 0" class="project-grid">
        <div 
          v-for="project in projectList" 
          :key="project.id" 
          class="project-card" 
          @click="$router.push(`/app/project-detail/${project.id}`)"
        >
          <div class="folder-visual">
            <div class="folder-icon-wrapper">
              <svg width="64" height="64" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 9C4 7.89543 4.89543 7 6 7H19L24 13H42C43.1046 13 44 13.8954 44 15V41C44 42.1046 43.1046 43 42 43H6C4.89543 43 4 42.1046 4 41V9Z" fill="#FFD466" stroke="#E8B339" stroke-width="2" stroke-linejoin="round"/>
              </svg>
              <span class="file-count-badge">{{ project.fileCount || 0 }}</span>
            </div>
          </div>

          <div class="project-info">
            <div class="project-name">{{ project.name }}</div>
            <div class="project-meta">
              {{ project.createTime }} · {{ project.category || '标注项目' }}
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <img class="empty-image" src="/image/uploadFolder.svg" alt="empty" />
        <h2>拖放文件夹到这里，开始项目</h2>
        <p>点击下方按钮，支持上传本地文件夹</p>
        <div class="empty-actions">
          <button type="button" class="primary" @click="$router.push('/app/publish')">去上传</button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const navItems = ['我的空间', '最近', '草稿箱', '回收站', '分享管理']
const tabs = ['全部', '作品', '我上传的']
const filters = ['颜色', '类别', '类型', '标签', '添加时间']

const activeNav = ref('我的空间')
const activeTab = ref('全部')

// 核心数据状态
const projectList = ref<any[]>([])

// 页面加载时从本地缓存获取数据
onMounted(() => {
  const data = localStorage.getItem('my_projects')
  if (data) {
    projectList.value = JSON.parse(data)
  }
})

// 排序功能逻辑
const toggleSort = () => {
  projectList.value.reverse()
}
</script>

<style scoped>
/* 页面基础背景 */
.history-page {
  background: #f5f5f7;
  min-height: 100vh;
  padding: 20px 24px;
  color: #1f2329;
}

/* 布局通用类 */
.top-nav, .toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-list, .tabs, .filters, .header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 导航项样式 */
.nav-item, .tab {
  border: none;
  background: transparent;
  color: #666f7a;
  font-size: 16px;
  padding: 8px 0;
  margin-right: 18px;
  cursor: pointer;
  position: relative;
}

.nav-item.active, .tab.active {
  color: #111;
  font-weight: 600;
}

.nav-item.active::after, .tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #111;
}

/* 按钮样式 */
.add-btn, .primary {
  background: #2d5cff;
  color: #fff;
  border: none;
  border-radius: 10px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.invite-btn {
  background: #fff;
  border: 1px solid #e4e6eb;
  border-radius: 10px;
  height: 38px;
  padding: 0 16px;
  cursor: pointer;
}

/* 工具栏 */
.toolbar {
  margin-top: 24px;
  border-bottom: 1px solid #eef0f2;
  padding-bottom: 8px;
}

.filter-btn {
  background: transparent;
  border: none;
  color: #2e3238;
  font-size: 14px;
  cursor: pointer;
}

.arrow { color: #9ba0a8; margin-left: 4px; }

.icon-btn {
  background: none;
  border: 1px solid #e4e6eb;
  border-radius: 6px;
  width: 32px;
  height: 32px;
  cursor: pointer;
}

/* 项目网格布局 */
.content-area {
  margin-top: 24px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 24px;
}

.project-card {
  background: #fff;
  border-radius: 16px;
  padding: 12px;
  border: 1px solid transparent;
  transition: all 0.25s ease;
  cursor: pointer;
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.06);
  border-color: #2d5cff;
}

/* 文件夹视觉风格 */
.folder-visual {
  width: 100%;
  height: 140px;
  background: #fcfcfd;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.folder-icon-wrapper {
  position: relative;
}

.file-count-badge {
  position: absolute;
  right: -8px;
  bottom: 8px;
  background: #2d5cff;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  border: 2px solid #fff;
}

.project-info {
  padding: 4px;
}

.project-name {
  font-weight: 600;
  font-size: 15px;
  color: #1f2329;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-meta {
  font-size: 12px;
  color: #8b93a1;
  margin-top: 4px;
}

/* 空状态样式 */
.empty-state {
  height: 60vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.empty-image { width: 180px; margin-bottom: 20px; }
h2 { font-size: 24px; margin-bottom: 10px; }
p { color: #8b93a1; margin-bottom: 24px; }
</style>