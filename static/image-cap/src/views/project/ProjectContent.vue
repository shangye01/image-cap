<template>
  <div class="project-content-page">
    <!-- 项目列表页 -->
    <template v-if="!currentProject">
      <div class="project-grid">
        <CreateBoardCard
          :existing-project-names="projectList.map((item) => item.projectName)"
          @create="handleCreateProject"
        />

        <div
          v-for="project in projectList"
          :key="project.id"
          class="project-folder-card"
          @click="enterProject(project)"
          @mouseenter="showRemark(project.id)"
          @mouseleave="hideRemark"
        >
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
        </div>
      </div>
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
          <div class="project-detail-title">{{ currentProject.projectName }}</div>
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
import { computed, ref, onBeforeUnmount } from 'vue'
import CreateBoardCard from '@/views/project/CreateBoardCard.vue'

const projectList = ref([])
const hoveredProjectId = ref(null)

const currentProjectId = ref(null)
const openedInnerFolderId = ref(null)

const previewVisible = ref(false)
const previewImageUrl = ref('')
const previewFileName = ref('')

const currentProject = computed(() => {
  return projectList.value.find((item) => item.id === currentProjectId.value) || null
})

const openedInnerFolder = computed(() => {
  if (!currentProject.value) return null
  return currentProject.value.folders.find((item) => item.id === openedInnerFolderId.value) || null
})

const handleCreateProject = (projectData) => {
  projectList.value.push(projectData)
}

const enterProject = (project) => {
  currentProjectId.value = project.id
  openedInnerFolderId.value = null
}

const backToProjectList = () => {
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

onBeforeUnmount(() => {
  if (previewImageUrl.value) {
    URL.revokeObjectURL(previewImageUrl.value)
  }
})
</script>

<style scoped>
.project-content-page {
  width: 100%;
  padding: 24px;
  box-sizing: border-box;
}

.project-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: flex-start;
}

.project-folder-card {
  width: 260px;
  cursor: pointer;
  user-select: none;
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
  border: none;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.18s ease, filter 0.18s ease, box-shadow 0.18s ease;
}

.file-action-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
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

.empty-folder-text {
  font-size: 13px;
  color: #9aa1a9;
  padding: 6px 2px;
}

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
</style>