<template>
  <div class="project-content-page">
    <!-- 1. 项目列表页 -->
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

    <!-- 2. 项目内部：文件夹列表页 -->
    <template v-else-if="currentProject && !currentFolder">
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
          @click="enterFolder(folder)"
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
    </template>

    <!-- 3. 文件夹内部：图片文件宫格页 -->
    <template v-else-if="currentProject && currentFolder">
      <div class="project-detail-header">
        <div class="project-nav">
          <button
            class="back-btn"
            type="button"
            @click="backToFolderList"
            aria-label="返回文件夹列表"
          >
            <span class="back-btn-icon">←</span>
          </button>

          <div class="breadcrumb">
            <span class="breadcrumb-link" @click="backToProjectList">项目列表</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-link" @click="backToFolderList">
              {{ currentProject.projectName }}
            </span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ currentFolder.name }}</span>
          </div>
        </div>

        <div class="project-detail-title-wrap">
          <div class="project-detail-title-row">
            <div class="project-detail-title">{{ currentFolder.name }}</div>
            <div class="folder-action-buttons">
              <button type="button" class="file-action-btn batch" @click="selectAllFilesInFolder">
                批量标注
              </button>
              <button type="button" class="file-action-btn work" @click="startSelectedWork">
                开始标注
              </button>
            </div>
          </div>

          <div class="project-detail-remark">共 {{ currentFolder.files.length }} 个文件</div>
        </div>
      </div>

      <div v-if="currentFolder.files.length" class="image-grid">
        <div v-for="file in currentFolder.files" :key="file.id" class="image-card">
          <label class="file-select-checkbox" @click.stop>
            <input
              type="checkbox"
              :checked="isFileSelected(file.id)"
              @change="toggleFileSelection(file.id)"
            />
          </label>
          <div class="image-card-preview" @click.stop="previewFile(file)">
            <template v-if="isImageFile(file) && getFilePreviewUrl(file)">
              <img :src="getFilePreviewUrl(file)" :alt="file.name" class="image-thumb" />
            </template>

            <template v-else-if="isImageFile(file)">
              <div class="image-placeholder">图片不可预览</div>
            </template>

            <template v-else>
              <div class="file-placeholder">📄</div>
            </template>
          </div>

          <div class="image-card-info">
            <div class="file-name-text" :title="file.name">{{ file.name }}</div>
          </div>

          <div class="image-card-actions">
            <button type="button" class="file-action-btn preview" @click.stop="previewFile(file)">
              预览
            </button>

            <button type="button" class="file-action-btn work" @click.stop="handleWork(file)">
              工作
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-folder-page">该文件夹暂无文件</div>
    </template>

    <!-- 工作弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="workVisible" class="dialog-mask" @click="closeWorkDialog">
          <div class="dialog-panel work-dialog-panel" @click.stop>
            <div class="work-dialog-header">
              <div class="dialog-title">工作</div>
              <button class="work-dialog-close" type="button" @click="closeWorkDialog">×</button>
            </div>

            <div class="dialog-body work-dialog-body">
              <div class="work-file-summary">
                {{ workSummaryText }}
              </div>

              <div class="mode-row">
                <label class="radio-item" @click="workForm.mode = 'keyword'">
                  <span class="radio-dot" :class="{ active: workForm.mode === 'keyword' }"></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'keyword' }">
                    关键词模型
                  </span>
                </label>

                <label class="radio-item" @click="workForm.mode = 'nonKeyword'">
                  <span
                    class="radio-dot"
                    :class="{ active: workForm.mode === 'nonKeyword' }"
                  ></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'nonKeyword' }">
                    非关键词模型
                  </span>
                </label>
              </div>

              <div v-if="workForm.mode === 'keyword'" class="tag-panel">
                <div class="selected-title">已选择的标签</div>

                <div class="selected-box">
                  <template v-if="workSelectedTags.length">
                    <div
                      v-for="tag in workSelectedTags"
                      :key="tag.id"
                      class="tag-chip selected"
                      :style="{ backgroundColor: tag.color }"
                    >
                      <span>{{ tag.name }}</span>
                      <button class="tag-remove" type="button" @click="removeWorkTag(tag.id)">
                        ×
                      </button>
                    </div>
                  </template>

                  <div v-else class="empty-text">请选择下方标签</div>
                </div>

                <div v-for="scene in scenes" :key="scene.id" class="scene-block">
                  <div class="scene-title">{{ scene.name }}</div>

                  <div class="scene-tags">
                    <button
                      v-for="tag in scene.tags"
                      :key="tag.id"
                      type="button"
                      class="tag-chip scene-chip"
                      :class="{ active: isWorkSelected(tag.id) }"
                      :style="{ backgroundColor: tag.color }"
                      @click="toggleWorkTag(tag)"
                    >
                      <span>{{ tag.name }}</span>
                      <span v-if="isWorkSelected(tag.id)" class="tag-remove small">×</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="closeWorkDialog">
                取消
              </button>
              <button class="dialog-btn primary" type="button" @click="confirmWorkDialog">
                确定
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

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
import { computed, reactive, ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import CreateBoardCard from '@/views/project/CreateBoardCard.vue'

import {
  createProject,
  listProjects,
  listProjectFiles,
  uploadProjectFile,
  getProjectFileDownloadUrl,
  deleteProjectApi,
} from '@/api/projectStorage'
import { useUserStore } from '@/stores/user'

const projectList = ref([])
const hoveredProjectId = ref(null)

const currentProjectId = ref(null)
const currentFolderId = ref(null)
const openedProjectMenuId = ref(null)

const searchKeyword = ref('')
const sortType = ref('created_desc')

const renameVisible = ref(false)
const renameProjectId = ref(null)
const renameValue = ref('')

const previewVisible = ref(false)
const previewImageUrl = ref('')
const previewFileName = ref('')

const workVisible = ref(false)
const currentWorkFileId = ref(null)
const workForm = reactive({
  mode: 'keyword',
  selectedTagIds: [],
})
const selectedFileIds = ref([])

const deletingProjectId = ref(null)

const userStore = useUserStore()
const router = useRouter()
const previewUrlMap = new Map()

const scenes = ref([
  {
    id: 1,
    name: '场景1',
    tags: [
      { id: 1, name: 'person', color: '#d9c2f2' },
      { id: 2, name: 'car', color: '#f4b4af' },
      { id: 3, name: 'dog', color: '#b8c9f6' },
      { id: 4, name: 'cat', color: '#ecd68d' },
      { id: 5, name: 'cow', color: '#a9cf96' },
    ],
  },
  {
    id: 2,
    name: '场景2',
    tags: [
      { id: 6, name: 'horse', color: '#aee9ec' },
      { id: 7, name: 'tag2', color: '#f2d562' },
      { id: 8, name: 'tag3', color: '#eea2ca' },
    ],
  },
])

const handleGlobalClick = () => closeProjectMenu()

const currentProject = computed(
  () => projectList.value.find((item) => item.id === currentProjectId.value) || null
)

const currentFolder = computed(() => {
  if (!currentProject.value || !currentFolderId.value) return null
  return currentProject.value.folders.find((item) => item.id === currentFolderId.value) || null
})

const currentWorkFile = computed(() => {
  if (!currentProject.value || !currentWorkFileId.value) return null

  for (const folder of currentProject.value.folders || []) {
    const matched = (folder.files || []).find((file) => file.id === currentWorkFileId.value)
    if (matched) return matched
  }

  return null
})

const selectedFiles = computed(() => {
  if (!currentFolder.value) return []
  return currentFolder.value.files.filter((file) => selectedFileIds.value.includes(file.id))
})

const workSummaryText = computed(() => {
  if (selectedFiles.value.length > 1) return `已选择 ${selectedFiles.value.length} 个文件`
  return `当前文件：${currentWorkFile.value?.name || ''}`
})

const allTags = computed(() => scenes.value.flatMap((scene) => scene.tags))

const workSelectedTags = computed(() =>
  allTags.value.filter((tag) => workForm.selectedTagIds.includes(tag.id))
)

const filteredProjectList = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  let list = [...projectList.value]
  if (keyword) {
    list = list.filter((project) => project.projectName.trim().toLowerCase().includes(keyword))
  }

  if (sortType.value === 'created_desc')
    list.sort((a, b) => Number(b.createdAt || 0) - Number(a.createdAt || 0))
  else if (sortType.value === 'created_asc')
    list.sort((a, b) => Number(a.createdAt || 0) - Number(b.createdAt || 0))
  else if (sortType.value === 'name_asc')
    list.sort((a, b) => a.projectName.localeCompare(b.projectName, 'zh-CN'))
  else if (sortType.value === 'name_desc')
    list.sort((a, b) => b.projectName.localeCompare(a.projectName, 'zh-CN'))

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

const mapBackendFile = (backendFile) => ({
  id: backendFile.id,
  name: backendFile.filename,
  relativePath: '',
  type: backendFile.mime_type || '',
  size: backendFile.size_bytes || 0,
  file: null,
  storageBackend: backendFile.storage_backend || 'supabase',
  downloadUrl: backendFile.download_url || getProjectFileDownloadUrl(backendFile.id),
  previewUrl:
    backendFile.preview_url ||
    backendFile.download_url ||
    getProjectFileDownloadUrl(backendFile.id),
})

const loadProjects = async () => {
  try {
    const owner = userStore.user?.username || 'default'
    const { data } = await listProjects(owner)
    const projectData = await Promise.all(
      (data || []).map(async (project) => {
        const fileResp = await listProjectFiles(project.id)
        return {
          id: project.id,
          projectName: project.name,
          remark: project.description || '',
          mode: 'keyword',
          selectedTagIds: [],
          selectedTags: [],
          createdAt: new Date(project.created_at).getTime(),
          folders: [
            {
              id: `pending_${project.id}`,
              name: '待标注',
              files: (fileResp.data || []).map(mapBackendFile),
            },
            { id: `labeling_${project.id}`, name: '标注中', files: [] },
            { id: `done_${project.id}`, name: '已标注', files: [] },
          ],
        }
      })
    )
    projectList.value = projectData
  } catch (error) {
    console.error('读取项目失败：', error)
    window.alert(error?.response?.data?.detail || '读取项目失败')
  }
}

const handleCreateProject = async (projectData) => {
  const owner_id = userStore.user?.username || 'default'
  try {
    const { data } = await createProject({
      name: projectData.projectName,
      description: projectData.remark || '',
      owner_id,
    })

    const pendingFolder = projectData.folders.find((folder) => folder.name === '待标注')
    const pendingFiles = pendingFolder?.files || []

    for (const item of pendingFiles) {
      if (item.file) {
        await uploadProjectFile(data.id, item.file, owner_id)
      }
    }

    await loadProjects()
  } catch (error) {
    console.error('创建项目失败：', error)
    window.alert(error?.response?.data?.detail || '创建项目失败')
  }
}

const enterProject = (project) => {
  closeProjectMenu()
  currentProjectId.value = project.id
  currentFolderId.value = null
}

const backToProjectList = () => {
  closeProjectMenu()
  currentProjectId.value = null
  currentFolderId.value = null
  selectedFileIds.value = []
}

const enterFolder = (folder) => {
  currentFolderId.value = folder.id
  selectedFileIds.value = []
}

const backToFolderList = () => {
  currentFolderId.value = null
  selectedFileIds.value = []
}

const showRemark = (id) => {
  hoveredProjectId.value = id
}

const hideRemark = () => {
  hoveredProjectId.value = null
}

const isImageFile = (file) => typeof file.type === 'string' && file.type.startsWith('image/')

const getFilePreviewUrl = (file) => {
  if (!isImageFile(file)) return ''

  if (file.file) {
    if (previewUrlMap.has(file.id)) return previewUrlMap.get(file.id)

    const url = URL.createObjectURL(file.file)
    previewUrlMap.set(file.id, url)
    return url
  }

  return file.previewUrl || file.downloadUrl || ''
}

const previewFile = (file) => {
  previewFileName.value = file.name || ''

  if (!isImageFile(file)) {
    const targetUrl = file.downloadUrl || getFilePreviewUrl(file)
    if (targetUrl) window.open(targetUrl, '_blank', 'noopener,noreferrer')
    return
  }

  const imageUrl = getFilePreviewUrl(file)
  if (!imageUrl) return

  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }

  previewImageUrl.value = imageUrl
  previewVisible.value = true
}

const closePreview = () => {
  previewVisible.value = false
  previewFileName.value = ''

  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }
  previewImageUrl.value = ''
}

const isWorkSelected = (id) => workForm.selectedTagIds.includes(id)

const toggleWorkTag = (tag) => {
  const index = workForm.selectedTagIds.indexOf(tag.id)
  if (index > -1) workForm.selectedTagIds.splice(index, 1)
  else workForm.selectedTagIds.push(tag.id)
}

const removeWorkTag = (id) => {
  const index = workForm.selectedTagIds.indexOf(id)
  if (index > -1) workForm.selectedTagIds.splice(index, 1)
}

const handleWork = (file) => {
  if (!currentProject.value) return

  selectedFileIds.value = [file.id]
  currentWorkFileId.value = file.id
  workForm.mode = currentProject.value.mode || 'keyword'
  workForm.selectedTagIds = []
  workVisible.value = true
}

const isFileSelected = (fileId) => selectedFileIds.value.includes(fileId)

const toggleFileSelection = (fileId) => {
  const index = selectedFileIds.value.indexOf(fileId)
  if (index > -1) selectedFileIds.value.splice(index, 1)
  else selectedFileIds.value.push(fileId)
}

const selectAllFilesInFolder = () => {
  if (!currentFolder.value) return
  selectedFileIds.value = currentFolder.value.files.map((file) => file.id)
}

const startSelectedWork = () => {
  if (!currentProject.value || !currentFolder.value) return
  if (!selectedFileIds.value.length) {
    window.alert('请先选择要标注的文件')
    return
  }

  currentWorkFileId.value = selectedFileIds.value[0]
  workForm.mode = currentProject.value.mode || 'keyword'
  workForm.selectedTagIds = []
  workVisible.value = true
}

const closeWorkDialog = () => {
  workVisible.value = false
  currentWorkFileId.value = null
  workForm.mode = 'keyword'
  workForm.selectedTagIds = []
}

const confirmWorkDialog = () => {
  if (!currentProject.value) return

  currentProject.value.mode = workForm.mode

  if (workForm.mode === 'nonKeyword') {
    currentProject.value.selectedTagIds = []
    currentProject.value.selectedTags = []
  } else {
    currentProject.value.selectedTagIds = [...workForm.selectedTagIds]
    currentProject.value.selectedTags = [...workSelectedTags.value]
  }

  const targetFile = currentWorkFile.value || selectedFiles.value[0] || null
  const sourceImage = targetFile ? getFilePreviewUrl(targetFile) : ''
  const sourceName = targetFile?.name || ''

  closeWorkDialog()

  router.push({
    path: '/app/annotate',
    query: {
      sourceImage,
      sourceName,
      sourceMode: workForm.mode,
    },
  })
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

const deleteProject = async (projectId) => {
  closeProjectMenu()

  if (deletingProjectId.value === projectId) return

  const target = projectList.value.find((item) => item.id === projectId)
  if (!target) return

  const confirmed = window.confirm(`确定删除项目“${target.projectName}”吗？`)
  if (!confirmed) return

  try {
    deletingProjectId.value = projectId

    await deleteProjectApi(projectId)

    if (currentProjectId.value === projectId) {
      backToProjectList()
    }

    await loadProjects()
  } catch (error) {
    console.error('删除项目失败：', error)
    window.alert(error?.response?.data?.detail || '删除项目失败')
  } finally {
    deletingProjectId.value = null
  }
}

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

watch(
  () => workForm.mode,
  (newMode) => {
    if (newMode === 'nonKeyword') workForm.selectedTagIds = []
  }
)

onMounted(() => {
  loadProjects()
  window.addEventListener('click', handleGlobalClick)
})

onBeforeUnmount(() => {
  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }

  previewUrlMap.forEach((url) => URL.revokeObjectURL(url))
  previewUrlMap.clear()

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
  position: relative;
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
  cursor: pointer;
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
  top: 42px;
  right: 0;
  min-width: 120px;
  padding: 8px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
  border: 1px solid rgba(229, 231, 235, 0.9);
}

.project-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  color: #1f2937;
  cursor: pointer;
}

.project-menu-item:hover {
  background: #f3f4f6;
}

.project-menu-item.danger {
  color: #dc2626;
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

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 18px;
}

.image-card {
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.folder-action-buttons {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.file-action-btn.batch {
  background: #e8f3ff;
  color: #1a6fd8;
}

.image-card {
  position: relative;
}

.file-select-checkbox {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.file-select-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.image-card-preview {
  width: 100%;
  aspect-ratio: 1 / 1;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}

.image-thumb {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #f8fafc;
}

.image-placeholder,
.file-placeholder {
  font-size: 14px;
  color: #9aa1a9;
}

.file-placeholder {
  font-size: 40px;
}

.image-card-info {
  padding: 12px 12px 8px;
}

.image-card-actions {
  padding: 0 12px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-folder-page,
.empty-project-state {
  font-size: 14px;
  color: #9aa1a9;
  padding: 12px 2px;
}

.empty-project-state {
  margin-top: 24px;
}

.dialog-btn,
.file-action-btn {
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.18s ease, filter 0.18s ease, box-shadow 0.18s ease;
}

.dialog-btn:hover,
.file-action-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
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

.dialog-panel.work-dialog-panel {
  width: min(840px, 96vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.work-dialog-header {
  padding: 22px 22px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.work-dialog-close {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: transparent;
  font-size: 26px;
  line-height: 1;
  color: #999;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
  flex-shrink: 0;
}

.work-dialog-close:hover {
  background: #f3f4f6;
  color: #666;
}

.dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-body {
  margin-top: 16px;
}

.work-dialog-body {
  padding: 18px 22px 0;
  overflow-y: auto;
}

.work-file-summary {
  margin-bottom: 16px;
  font-size: 14px;
  color: #6b7280;
  word-break: break-all;
}

.work-file-summary span {
  color: #111827;
  font-weight: 600;
}

.mode-row {
  display: flex;
  align-items: center;
  gap: 48px;
  margin: 8px 0 18px;
  flex-wrap: wrap;
}

.radio-item {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.radio-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #a6a6a6;
  margin-right: 10px;
  box-sizing: border-box;
  position: relative;
  flex-shrink: 0;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.radio-dot.active {
  border-color: #3c8596;
}

.radio-dot.active::after {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 50%;
  background: #3c8596;
}

.radio-item:hover .radio-dot {
  transform: scale(1.05);
}

.radio-text {
  font-size: 15px;
  color: #737373;
}

.radio-text.strong {
  font-weight: 700;
  color: #1f2937;
}

.tag-panel {
  background: #fafafa;
  border-radius: 10px;
  padding: 16px;
}

.selected-title {
  font-size: 15px;
  color: #2b2f36;
  margin-bottom: 10px;
  font-weight: 600;
}

.selected-box {
  min-height: 76px;
  border: 2px solid #b8b8b8;
  border-radius: 14px;
  background: #fff;
  padding: 14px;
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}

.scene-block {
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid #dddddd;
}

.scene-title {
  font-size: 15px;
  font-weight: 700;
  color: #2b2f36;
  margin-bottom: 14px;
}

.scene-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tag-chip {
  position: relative;
  border: none;
  border-radius: 14px;
  padding: 10px 14px;
  font-size: 14px;
  color: #2d3748;
  cursor: pointer;
  line-height: 1;
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.tag-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
  filter: brightness(1.02);
}

.tag-chip.selected {
  padding-right: 32px;
}

.scene-chip.active {
  box-shadow: 0 0 0 2px rgba(88, 121, 91, 0.16);
}

.tag-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #95a47b;
  background: #dce8cb;
  color: #7d8e68;
  font-size: 18px;
  line-height: 16px;
  cursor: pointer;
  padding: 0;
}

.tag-remove.small {
  position: absolute;
  top: -8px;
  right: -8px;
}

.empty-text {
  font-size: 13px;
  color: #9aa1a9;
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

.work-dialog-panel .dialog-footer {
  margin-top: 0;
  padding: 20px 32px 28px;
  justify-content: flex-end;
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

  .image-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}
</style>