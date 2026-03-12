<template>
  <div class="project-content-page">
    <!-- 项目列表页 -->
    <template v-if="!currentProject">
      <div class="project-toolbar">
        <div class="toolbar-left">
          <input
            v-model="searchKeyword"
            class="toolbar-input"
            type="text"
            placeholder="搜索项目名"
          />

          <select v-model="sortType" class="toolbar-select">
            <option value="created_desc">按创建时间（新到旧）</option>
            <option value="created_asc">按创建时间（旧到新）</option>
            <option value="name_asc">按项目名（A-Z）</option>
            <option value="name_desc">按项目名（Z-A）</option>
          </select>
        </div>

        <div class="toolbar-right">
          <div class="project-count">共 {{ filteredProjectList.length }} 个项目</div>
        </div>
      </div>

      <div class="project-grid">
        <CreateBoardCard
          :existing-project-names="projectList.map((item) => item.projectName)"
          @create="handleCreateProject"
        />

        <div
          v-for="project in filteredProjectList"
          :key="project.id"
          class="project-folder-card"
          @mouseenter="showRemark(project.id)"
          @mouseleave="hideRemark"
        >
          <div class="project-card-menu-wrap">
            <button
              class="project-menu-trigger"
              type="button"
              @click.stop="toggleProjectMenu(project.id)"
            >
              ⋯
            </button>

            <transition name="menu-fade">
              <div v-if="openedProjectMenuId === project.id" class="project-menu-dropdown">
                <button
                  class="project-menu-item"
                  type="button"
                  @click.stop="handleRenameFromMenu(project)"
                >
                  重命名
                </button>
                <button
                  class="project-menu-item danger"
                  type="button"
                  @click.stop="handleDeleteFromMenu(project.id)"
                >
                  删除
                </button>
              </div>
            </transition>
          </div>

          <div class="folder-click-area" @click="enterProject(project)">
            <div class="folder-preview">
              <transition name="mask-fade">
                <div
                  v-if="hoveredProjectId === project.id && project.remark"
                  class="folder-remark-mask"
                >
                  <div class="folder-remark-text">
                    {{ project.remark }}
                  </div>
                </div>
              </transition>

              <div class="folder-shape">
                <div class="folder-tab"></div>
              </div>
            </div>

            <div class="folder-name">
              {{ project.projectName }}
            </div>

            <div class="folder-meta">
              <span>{{ project.mode === 'keyword' ? '关键词模型' : '非关键词模型' }}</span>
              <span>{{ formatDate(project.createdAt) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!filteredProjectList.length" class="empty-project-state">没有匹配的项目</div>
    </template>

    <!-- 项目内部页 -->
    <template v-else>
      <div class="project-detail-header">
        <div class="project-nav">
          <button
            class="back-btn"
            type="button"
            @click="backToProjectList"
            aria-label="返回项目列表"
          >
            <span class="back-btn-icon">←</span>
          </button>

          <div class="breadcrumb">
            <span class="breadcrumb-link" @click="backToProjectList">项目列表</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ currentProject.projectName }}</span>
          </div>
        </div>

        <div class="project-detail-title-wrap">
          <div class="project-detail-title-row">
            <div class="project-detail-title">{{ currentProject.projectName }}</div>

            <button class="mini-action-btn" type="button" @click="openRenameDialog(currentProject)">
              重命名
            </button>

            <button class="mini-action-btn danger" type="button" @click="deleteCurrentProject">
              删除项目
            </button>
          </div>

          <div v-if="currentProject.remark" class="project-detail-remark">
            {{ currentProject.remark }}
          </div>
        </div>
      </div>

      <div class="project-grid">
        <div
          v-for="folder in currentProject.folders"
          :key="folder.id"
          class="project-folder-card child-folder-card"
          @click="toggleInnerFolder(folder.id)"
        >
          <div class="folder-preview small-folder-preview">
            <div class="folder-shape">
              <div class="folder-tab"></div>
            </div>
          </div>

          <div class="folder-name">
            {{ folder.name }}
          </div>

          <div class="folder-count">{{ folder.files.length }} 个文件</div>
        </div>
      </div>

      <div v-if="openedInnerFolder" class="inner-folder-panel">
        <div class="inner-folder-panel-title">
          {{ openedInnerFolder.name }}
        </div>

        <div class="file-list">
          <template v-if="openedInnerFolder.files.length">
            <div v-for="file in openedInnerFolder.files" :key="file.id" class="file-item">
              <div class="file-main">
                <div class="file-icon">
                  {{ isImageFile(file) ? '🖼️' : '📄' }}
                </div>

                <div class="file-info">
                  <div class="file-name-text">{{ file.name }}</div>
                  <div v-if="file.relativePath" class="file-path-text">
                    {{ file.relativePath }}
                  </div>
                </div>

                <div class="file-actions">
                  <button
                    v-if="isImageFile(file)"
                    type="button"
                    class="file-action-btn preview"
                    @click.stop="previewFile(file)"
                  >
                    预览
                  </button>

                  <button type="button" class="file-action-btn work" @click.stop="handleWork(file)">
                    工作
                  </button>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="empty-folder-text">暂无文件</div>
        </div>
      </div>
    </template>

    <!-- 重命名弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="renameVisible" class="dialog-mask" @click="closeRenameDialog">
          <div class="dialog-panel" @click.stop>
            <div class="dialog-title">重命名项目</div>

            <div class="dialog-body">
              <input
                v-model="renameValue"
                class="dialog-input"
                type="text"
                placeholder="请输入新的项目名"
              />

              <div v-if="renameError" class="dialog-error">
                {{ renameError }}
              </div>
            </div>

            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="closeRenameDialog">
                取消
              </button>
              <button class="dialog-btn primary" type="button" @click="confirmRename">确定</button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- 图片预览弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="previewVisible" class="preview-mask" @click="closePreview">
          <div class="preview-panel" @click.stop>
            <button class="preview-close-btn" type="button" @click="closePreview">×</button>

            <div class="preview-content">
              <img
                v-if="previewImageUrl"
                :src="previewImageUrl"
                :alt="previewFileName"
                class="preview-image"
              />
            </div>

            <div class="preview-footer">
              <div class="preview-file-name">{{ previewFileName }}</div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { computed, ref, onBeforeUnmount, onMounted, watch } from 'vue'
import CreateBoardCard from '@/views/project/CreateBoardCard.vue'

const STORAGE_KEY = 'image-cap-projects-v1'

const projectList = ref([])
const hoveredProjectId = ref(null)

const currentProjectId = ref(null)
const openedInnerFolderId = ref(null)
const openedProjectMenuId = ref(null)

const searchKeyword = ref('')
const sortType = ref('created_desc')

const renameVisible = ref(false)
const renameProjectId = ref(null)
const renameValue = ref('')

const previewVisible = ref(false)
const previewImageUrl = ref('')
const previewFileName = ref('')

const handleGlobalClick = () => {
  closeProjectMenu()
}

const currentProject = computed(() => {
  return projectList.value.find((item) => item.id === currentProjectId.value) || null
})

const openedInnerFolder = computed(() => {
  if (!currentProject.value) return null
  return currentProject.value.folders.find((item) => item.id === openedInnerFolderId.value) || null
})

const filteredProjectList = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  let list = [...projectList.value]

  if (keyword) {
    list = list.filter((project) => project.projectName.trim().toLowerCase().includes(keyword))
  }

  if (sortType.value === 'created_desc') {
    list.sort((a, b) => Number(b.createdAt || 0) - Number(a.createdAt || 0))
  } else if (sortType.value === 'created_asc') {
    list.sort((a, b) => Number(a.createdAt || 0) - Number(b.createdAt || 0))
  } else if (sortType.value === 'name_asc') {
    list.sort((a, b) => a.projectName.localeCompare(b.projectName, 'zh-CN'))
  } else if (sortType.value === 'name_desc') {
    list.sort((a, b) => b.projectName.localeCompare(a.projectName, 'zh-CN'))
  }

  return list
})

const renameError = computed(() => {
  if (!renameVisible.value) return ''

  const name = renameValue.value.trim()
  if (!name) return '请输入项目名'

  const exists = projectList.value.some((project) => {
    if (project.id === renameProjectId.value) return false
    return project.projectName.trim().toLowerCase() === name.toLowerCase()
  })

  if (exists) return '项目名已存在，请更换一个名称'
  return ''
})

const persistProjects = () => {
  try {
    const serializable = projectList.value.map((project) => ({
      ...project,
      folders: (project.folders || []).map((folder) => ({
        ...folder,
        files: (folder.files || []).map((file) => ({
          id: file.id,
          name: file.name,
          relativePath: file.relativePath || '',
          type: file.type || '',
          size: file.size || 0,
        })),
      })),
    }))

    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable))
  } catch (error) {
    console.error('保存项目失败：', error)
  }
}

const loadProjects = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      projectList.value = parsed
    }
  } catch (error) {
    console.error('读取项目失败：', error)
  }
}

const handleCreateProject = (projectData) => {
  const name = projectData.projectName.trim().toLowerCase()

  const exists = projectList.value.some(
    (project) => project.projectName.trim().toLowerCase() === name
  )

  if (exists) {
    return
  }

  projectList.value.push({
    ...projectData,
    createdAt: Date.now(),
  })
}

const enterProject = (project) => {
  closeProjectMenu()
  currentProjectId.value = project.id
  openedInnerFolderId.value = null
}

const backToProjectList = () => {
  closeProjectMenu()
  currentProjectId.value = null
  openedInnerFolderId.value = null
}

const toggleInnerFolder = (folderId) => {
  openedInnerFolderId.value = openedInnerFolderId.value === folderId ? null : folderId
}

const showRemark = (id) => {
  hoveredProjectId.value = id
}

const hideRemark = () => {
  hoveredProjectId.value = null
}

const isImageFile = (file) => {
  return typeof file.type === 'string' && file.type.startsWith('image/')
}

const previewFile = (file) => {
  if (!isImageFile(file) || !file.file) return

  if (previewImageUrl.value) {
    URL.revokeObjectURL(previewImageUrl.value)
  }

  previewImageUrl.value = URL.createObjectURL(file.file)
  previewFileName.value = file.name
  previewVisible.value = true
}

const closePreview = () => {
  previewVisible.value = false
  previewFileName.value = ''

  if (previewImageUrl.value) {
    URL.revokeObjectURL(previewImageUrl.value)
    previewImageUrl.value = ''
  }
}

const handleWork = (file) => {
  console.log('点击工作按钮：', file)
}

const openRenameDialog = (project) => {
  closeProjectMenu()
  renameProjectId.value = project.id
  renameValue.value = project.projectName
  renameVisible.value = true
}

const closeRenameDialog = () => {
  renameVisible.value = false
  renameProjectId.value = null
  renameValue.value = ''
}

const confirmRename = () => {
  if (renameError.value) return

  const target = projectList.value.find((item) => item.id === renameProjectId.value)
  if (!target) return

  target.projectName = renameValue.value.trim()
  closeRenameDialog()
}

const deleteProject = (projectId) => {
  closeProjectMenu()

  const target = projectList.value.find((item) => item.id === projectId)
  if (!target) return

  const confirmed = window.confirm(`确定删除项目“${target.projectName}”吗？`)
  if (!confirmed) return

  projectList.value = projectList.value.filter((item) => item.id !== projectId)

  if (currentProjectId.value === projectId) {
    backToProjectList()
  }
}

const deleteCurrentProject = () => {
  if (!currentProject.value) return
  deleteProject(currentProject.value.id)
}

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

watch(projectList, persistProjects, { deep: true })

onMounted(() => {
  loadProjects()
  window.addEventListener('click', handleGlobalClick)
})

onBeforeUnmount(() => {
  if (previewImageUrl.value) {
    URL.revokeObjectURL(previewImageUrl.value)
  }
  window.removeEventListener('click', handleGlobalClick)
})

const toggleProjectMenu = (projectId) => {
  openedProjectMenuId.value = openedProjectMenuId.value === projectId ? null : projectId
}

const closeProjectMenu = () => {
  openedProjectMenuId.value = null
}

const handleRenameFromMenu = (project) => {
  closeProjectMenu()
  openRenameDialog(project)
}

const handleDeleteFromMenu = (projectId) => {
  closeProjectMenu()
  deleteProject(projectId)
}
</script>

<style scoped>
.project-content-page {
  width: 100%;
  padding: 24px;
  box-sizing: border-box;
}

.project-toolbar {
  margin-bottom: 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-input,
.toolbar-select {
  height: 42px;
  border: 1px solid #d8dee6;
  border-radius: 12px;
  background: #fff;
  font-size: 14px;
  color: #111827;
  box-sizing: border-box;
  outline: none;
}

.toolbar-input {
  width: 240px;
  padding: 0 14px;
}

.toolbar-select {
  padding: 0 14px;
}

.toolbar-input:focus,
.toolbar-select:focus {
  border-color: #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.12);
}

.project-count {
  font-size: 14px;
  color: #6b7280;
}

.project-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: flex-start;
}

.project-folder-card {
  width: 260px;
  user-select: none;
}

.folder-click-area {
  cursor: pointer;
}

.folder-preview {
  position: relative;
  width: 100%;
  height: 185px;
  border-radius: 18px;
  background: #f7f7f7;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.project-folder-card:hover .folder-preview {
  background: #f3f4f6;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
}

.small-folder-preview {
  height: 160px;
}

.folder-shape {
  position: relative;
  width: 92px;
  height: 60px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f6cf70, #efbc46);
  box-shadow: inset 0 -4px 0 rgba(0, 0, 0, 0.05);
  z-index: 1;
}

.folder-tab {
  position: absolute;
  top: -10px;
  left: 12px;
  width: 34px;
  height: 16px;
  border-radius: 10px 10px 0 0;
  background: #e9b94d;
}

.folder-name {
  margin-top: 16px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  color: #111827;
  word-break: break-word;
}

.folder-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
}

.mini-action-btn,
.dialog-btn,
.file-action-btn {
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.18s ease, filter 0.18s ease, box-shadow 0.18s ease;
}

.mini-action-btn {
  padding: 8px 14px;
  font-size: 13px;
  background: #eef2f7;
  color: #374151;
}

.mini-action-btn:hover,
.dialog-btn:hover,
.file-action-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
}

.mini-action-btn.danger {
  background: #fee2e2;
  color: #b91c1c;
}

.project-folder-card {
  position: relative;
  width: 260px;
  user-select: none;
}

.project-card-menu-wrap {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
}

.project-menu-trigger {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: #4b5563;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.project-menu-trigger:hover {
  background: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.project-menu-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 120px;
  padding: 6px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.14);
  border: 1px solid #edf0f4;
}

.project-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  color: #374151;
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.project-menu-item:hover {
  background: #f3f4f6;
}

.project-menu-item.danger {
  color: #b91c1c;
}

.project-menu-item.danger:hover {
  background: #fef2f2;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.folder-count {
  margin-top: 8px;
  font-size: 14px;
  color: #6b7280;
}

.folder-remark-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  background: rgba(17, 24, 39, 0.58);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  box-sizing: border-box;
}

.folder-remark-text {
  max-width: 100%;
  max-height: 100%;
  overflow-y: auto;
  color: #ffffff;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
  word-break: break-word;
  white-space: pre-wrap;
}

.project-detail-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 28px;
}

.project-nav {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 44px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #e5e7eb;
  border-radius: 50%;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease,
    border-color 0.18s ease;
}

.back-btn:hover {
  background: #f8fafc;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.back-btn:active {
  transform: translateY(0);
}

.back-btn-icon {
  font-size: 18px;
  line-height: 1;
  transform: translateX(-1px);
}

.breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.breadcrumb-link {
  color: #6b7280;
  cursor: pointer;
  transition: color 0.18s ease;
}

.breadcrumb-link:hover {
  color: #111827;
}

.breadcrumb-separator {
  color: #c0c4cc;
}

.breadcrumb-current {
  color: #111827;
  font-weight: 600;
  word-break: break-word;
}

.project-detail-title-wrap {
  min-width: 0;
}

.project-detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.project-detail-title {
  font-size: 28px;
  font-weight: 800;
  color: #111827;
  line-height: 1.3;
}

.project-detail-remark {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: #6b7280;
  white-space: pre-wrap;
  word-break: break-word;
}

.inner-folder-panel {
  margin-top: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #fff;
  overflow: hidden;
}

.inner-folder-panel-title {
  padding: 16px 18px;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  background: #f8fafc;
  border-bottom: 1px solid #eef2f7;
}

.file-list {
  padding: 14px;
}

.file-item + .file-item {
  margin-top: 10px;
}

.file-item {
  border-radius: 14px;
  background: #f8fafc;
  padding: 12px 14px;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.file-item:hover {
  background: #eef6fb;
  transform: translateY(-1px);
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.file-action-btn {
  padding: 6px 12px;
  font-size: 12px;
  line-height: 1;
}

.file-action-btn.preview {
  background: #e0f2fe;
  color: #0369a1;
}

.file-action-btn.work {
  background: #dcfce7;
  color: #166534;
}

.file-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.file-icon {
  font-size: 16px;
  line-height: 1.2;
}

.file-info {
  min-width: 0;
  flex: 1;
}

.file-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}

.file-path-text {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}

.empty-folder-text,
.empty-project-state {
  font-size: 13px;
  color: #9aa1a9;
  padding: 6px 2px;
}

.empty-project-state {
  margin-top: 24px;
}

.dialog-mask,
.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.dialog-panel {
  width: min(420px, 92vw);
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  padding: 22px;
  box-sizing: border-box;
}

.dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-body {
  margin-top: 16px;
}

.dialog-input {
  width: 100%;
  height: 44px;
  border: 1px solid #d8dee6;
  border-radius: 12px;
  padding: 0 14px;
  box-sizing: border-box;
  outline: none;
  font-size: 14px;
}

.dialog-input:focus {
  border-color: #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.12);
}

.dialog-error {
  margin-top: 8px;
  font-size: 13px;
  color: #d14343;
}

.dialog-footer {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-btn {
  padding: 9px 16px;
  font-size: 14px;
}

.dialog-btn.secondary {
  background: #eef2f7;
  color: #374151;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #43c7db, #2faec6);
  color: #fff;
}

.preview-panel {
  position: relative;
  width: min(980px, 92vw);
  max-height: 90vh;
  background: #ffffff;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  display: flex;
  flex-direction: column;
}

.preview-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(17, 24, 39, 0.72);
  color: #fff;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.preview-content {
  flex: 1;
  min-height: 0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 24px;
  box-sizing: border-box;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 12px;
}

.preview-footer {
  padding: 14px 18px 18px;
  border-top: 1px solid #eef2f7;
}

.preview-file-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}

.mask-fade-enter-active,
.mask-fade-leave-active,
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.2s ease;
}

.mask-fade-enter-from,
.mask-fade-leave-to,
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .project-content-page {
    padding: 16px;
  }

  .project-toolbar {
    margin-bottom: 18px;
  }

  .toolbar-input {
    width: 100%;
  }

  .project-detail-title {
    font-size: 24px;
  }
}
</style>