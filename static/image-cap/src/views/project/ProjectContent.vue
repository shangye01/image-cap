<template>
  <div class="project-content-page">
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
          </div>
          <div class="project-detail-remark">共 {{ currentFolder.files.length }} 个文件</div>
        </div>
      </div>

      <div v-if="currentFolder.files.length" class="batch-action-toolbar">
        <div class="batch-toolbar-left">
          <label class="checkbox-wrapper" @click.stop="toggleSelectAll">
            <div class="custom-checkbox" :class="{ checked: isAllSelected }">
              <span v-if="isAllSelected">✓</span>
            </div>
            <span class="checkbox-label">全选图片</span>
          </label>
          <div class="selection-info">已选择 {{ selectedFileIds.length }} 张图片</div>
        </div>
        <div class="batch-toolbar-right">
          <button 
            class="batch-label-btn" 
            :disabled="selectedFileIds.length === 0"
            @click="openAutoLabelDialog"
          >
            ✨ 一键自动标注
          </button>
        </div>
      </div>

    <div v-if="currentFolder.files.length" class="image-grid">
        <div 
          v-for="file in currentFolder.files" 
          :key="file.id" 
          class="image-card"
          :class="{ 'is-selected': selectedFileIds.includes(file.id) }"
          @click="toggleFileSelection(file.id)"
        >
          <div v-if="selectedFileIds.includes(file.id)" class="selection-badge">
            ✓
          </div>

          <div class="image-card-preview">
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
            <div class="file-name-text">{{ file.name }}</div>
            <div v-if="file.relativePath" class="file-path-text">
              {{ file.relativePath }}
            </div>
          </div>

          <div class="image-card-actions">
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

      <div v-else class="empty-folder-page">该文件夹暂无文件</div>
    </template>

    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="autoLabelVisible" class="dialog-mask" @click="autoLabelVisible = false">
          <div class="dialog-panel" @click.stop>
            <div class="dialog-title">AI 自动标注</div>
            <div class="dialog-body">
              <div class="dialog-field">
                <label class="field-label">选择识别模型</label>
                <select v-model="autoLabelModel" class="dialog-input">
                  <option value="general">通用场景模型 (V3)</option>
                  <option value="detail">高精度细节模型 (Pro)</option>
                  <option value="aesthetic">艺术/审美评分模型</option>
                </select>
              </div>
              <div class="dialog-remark-box">
                提示：即将对 <strong>{{ selectedFileIds.length }}</strong> 张图片进行批量标注，这需要花费一定时间。
              </div>
            </div>
            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="autoLabelVisible = false">
                取消
              </button>
              <button class="dialog-btn primary" type="button" @click="confirmAutoLabel">
                开始标注
              </button>
            </div>
          </div>
        </div>
      </transition>

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

      <transition name="preview-fade">
        <div v-if="workVisible" class="dialog-mask" @click="closeWorkDialog">
          <div class="dialog-panel work-dialog-panel" @click.stop>
            <div class="work-dialog-header">
              <div class="dialog-title">工作</div>
              <button class="work-dialog-close" type="button" @click="closeWorkDialog">×</button>
            </div>

            <div class="dialog-body work-dialog-body">
              <div class="work-file-summary">
                当前文件：<span>{{ currentWorkFile?.name || '' }}</span>
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
  </div>
</template>

<script setup>
import { computed, reactive, ref, onBeforeUnmount, onMounted, watch } from 'vue'
import CreateBoardCard from '@/views/project/CreateBoardCard.vue'

const STORAGE_KEY = 'image-cap-projects-v1'

const projectList = ref([])
const hoveredProjectId = ref(null)

const currentProjectId = ref(null)
const currentFolderId = ref(null)
const openedProjectMenuId = ref(null)

const searchKeyword = ref('')
const sortType = ref('created_desc')

// --- 批量选择与标注 (新增) ---
const selectedFileIds = ref([]) // 用于存储选中的图片ID
const autoLabelVisible = ref(false)
const autoLabelModel = ref('general')

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

const previewUrlMap = new Map()

const scenes = ref([
  {
    id: 1,
    name: '场景1',
    tags: [
      { id: 1, name: '标签1', color: '#d9c2f2' },
      { id: 2, name: '标签2', color: '#f4b4af' },
      { id: 3, name: '标签3', color: '#b8c9f6' },
      { id: 4, name: '标签4', color: '#ecd68d' },
      { id: 5, name: '标签5', color: '#a9cf96' },
    ],
  },
  {
    id: 2,
    name: '场景2',
    tags: [
      { id: 6, name: '标签1', color: '#aee9ec' },
      { id: 7, name: '标签2', color: '#f2d562' },
      { id: 8, name: '标签3', color: '#eea2ca' },
    ],
  },
])

const handleGlobalClick = () => {
  closeProjectMenu()
}

const currentProject = computed(() => {
  return projectList.value.find((item) => item.id === currentProjectId.value) || null
})

const currentFolder = computed(() => {
  if (!currentProject.value || !currentFolderId.value) return null
  return currentProject.value.folders.find((item) => item.id === currentFolderId.value) || null
})

// --- 批量逻辑计算与方法 (新增) ---
const isAllSelected = computed(() => {
  if (!currentFolder.value || currentFolder.value.files.length === 0) return false
  return selectedFileIds.value.length === currentFolder.value.files.length
})

const toggleFileSelection = (id) => {
  const index = selectedFileIds.value.indexOf(id)
  if (index > -1) {
    selectedFileIds.value.splice(index, 1) // 已存在则取消选中
  } else {
    selectedFileIds.value.push(id) // 不存在则添加选中
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedFileIds.value = [] // 取消全选
  } else {
    selectedFileIds.value = currentFolder.value.files.map(f => f.id) // 全选
  }
}

const openAutoLabelDialog = () => {
  autoLabelVisible.value = true
}

const confirmAutoLabel = () => {
  console.log('执行标注, 文件IDs:', selectedFileIds.value, '模型:', autoLabelModel.value)
  // 此处可接入真实的 API 调用
  autoLabelVisible.value = false
  alert(`成功提交 ${selectedFileIds.value.length} 张图片的自动标注请求！`)
  selectedFileIds.value = [] // 标注后清空选中状态
}

const currentWorkFile = computed(() => {
  if (!currentProject.value || !currentWorkFileId.value) return null

  for (const folder of currentProject.value.folders || []) {
    const matched = (folder.files || []).find((file) => file.id === currentWorkFileId.value)
    if (matched) return matched
  }

  return null
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
      selectedTagIds: Array.isArray(project.selectedTagIds) ? [...project.selectedTagIds] : [],
      selectedTags: Array.isArray(project.selectedTags) ? [...project.selectedTags] : [],
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
      projectList.value = parsed.map((project) => ({
        ...project,
        mode: project.mode || 'keyword',
        selectedTagIds: Array.isArray(project.selectedTagIds)
          ? project.selectedTagIds
          : Array.isArray(project.selectedTags)
          ? project.selectedTags.map((tag) => tag.id)
          : [],
        selectedTags: Array.isArray(project.selectedTags) ? project.selectedTags : [],
      }))
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
    mode: projectData.mode || 'keyword',
    selectedTagIds: Array.isArray(projectData.selectedTagIds)
      ? [...projectData.selectedTagIds]
      : [],
    selectedTags: Array.isArray(projectData.selectedTags) ? [...projectData.selectedTags] : [],
    createdAt: Date.now(),
  })
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
}

const enterFolder = (folder) => {
  currentFolderId.value = folder.id
}

const backToFolderList = () => {
  currentFolderId.value = null
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

const getFilePreviewUrl = (file) => {
  if (!isImageFile(file) || !file.file) return ''

  if (previewUrlMap.has(file.id)) {
    return previewUrlMap.get(file.id)
  }

  const url = URL.createObjectURL(file.file)
  previewUrlMap.set(file.id, url)
  return url
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

const isWorkSelected = (id) => {
  return workForm.selectedTagIds.includes(id)
}

const toggleWorkTag = (tag) => {
  const index = workForm.selectedTagIds.indexOf(tag.id)
  if (index > -1) {
    workForm.selectedTagIds.splice(index, 1)
  } else {
    workForm.selectedTagIds.push(tag.id)
  }
}

const removeWorkTag = (id) => {
  const index = workForm.selectedTagIds.indexOf(id)
  if (index > -1) {
    workForm.selectedTagIds.splice(index, 1)
  }
}

const handleWork = (file) => {
  if (!currentProject.value) return

  currentWorkFileId.value = file.id
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

  closeWorkDialog()
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
    if (newMode === 'nonKeyword') {
      workForm.selectedTagIds = []
    }
  }
)

watch(projectList, persistProjects, { deep: true })

// --- 切换路径时自动清空选择 (防止跨层级误操作) ---
watch([currentProjectId, currentFolderId], () => {
  selectedFileIds.value = []
})

onMounted(() => {
  loadProjects()
  window.addEventListener('click', handleGlobalClick)
})

onBeforeUnmount(() => {
  if (previewImageUrl.value) {
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
/* ========================================= */
/* --- 新增：批量标注工具栏样式 --- */
/* ========================================= */
.batch-action-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #f0f9fa; /* 呼应主题的青色背景 */
  border: 1px solid #d1e9ec;
  border-radius: 14px;
  margin-bottom: 24px;
}

.batch-toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.custom-checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid #a6cdd4;
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  transition: all 0.2s ease;
}

.custom-checkbox.checked {
  background: #45b8cb;
  border-color: #45b8cb;
}

.checkbox-label {
  font-size: 14px;
  font-weight: 600;
  color: #3c8596;
}

.selection-info {
  font-size: 13px;
  color: #6b7280;
}

.selection-info span {
  color: #45b8cb;
  font-weight: 700;
}

.batch-label-btn {
  border: none;
  background: linear-gradient(135deg, #43c7db, #2faec6);
  color: #fff;
  padding: 8px 20px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.batch-label-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(69, 184, 203, 0.3);
}

.batch-label-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

/* --- 新增：卡片选中样式 --- */
.image-card.is-selected {
  border: 2px solid #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.1);
}

.selection-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 5;
  width: 24px;
  height: 24px;
  background: #45b8cb;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.dialog-field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.dialog-remark-box {
  margin-top: 12px;
  font-size: 13px;
  color: #4b5563;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 4px solid #45b8cb;
}

/* ========================================= */
/* --- 以下为原有样式 (保持不变) --- */
/* ========================================= */

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

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 18px;
}

.image-card {
  position: relative;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  transition: all 0.2s ease;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
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
  object-fit: cover;
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
  word-break: break-all;
}

.file-path-text {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
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