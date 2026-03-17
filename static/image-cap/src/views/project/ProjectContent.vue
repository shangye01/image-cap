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
          <div class="selection-info">已选择 <span>{{ selectedFileIds.length }}</span> 张图片</div>
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
          <div class="dialog-panel work-dialog-panel" @click.stop>
            <div class="work-dialog-header">
              <div class="dialog-title">🤖 智能预标注设置</div>
              <button class="work-dialog-close" type="button" @click="autoLabelVisible = false">×</button>
            </div>

            <div class="dialog-body work-dialog-body">
              <div class="dialog-field" style="margin-bottom: 20px;">
                <label class="field-label">选择目标模型库：</label>
                <select v-model="autoLabelModel" class="dialog-input">
                  <option v-for="model in trainingStatus.local_models" :key="model.name" :value="model.name">
                    {{ model.name }} {{ model.is_active ? '(当前使用)' : '' }}
                  </option>
                  <option v-if="trainingStatus.local_models.length === 0" value="yolov8n">
                    yolov8n (默认模型)
                  </option>
                </select>
              </div>

              <div class="mode-row">
                <label class="radio-item" @click="autoLabelMode = 'all'">
                  <span class="radio-dot" :class="{ active: autoLabelMode === 'all' }"></span>
                  <span class="radio-text" :class="{ strong: autoLabelMode === 'all' }">识别所有目标</span>
                </label>

                <label class="radio-item" @click="autoLabelMode = 'keyword'">
                  <span class="radio-dot" :class="{ active: autoLabelMode === 'keyword' }"></span>
                  <span class="radio-text" :class="{ strong: autoLabelMode === 'keyword' }">仅标注指定关键词</span>
                </label>
              </div>

              <div v-if="autoLabelMode === 'keyword'" class="tag-panel">
                <div class="selected-title">已选择的过滤标签</div>
                <div class="selected-box">
                  <template v-if="autoLabelSelectedTags.length">
                    <div
                      v-for="tag in autoLabelSelectedTags"
                      :key="tag.id"
                      class="tag-chip selected"
                      :style="{ backgroundColor: tag.color, color: '#fff' }"
                    >
                      <span>{{ tag.name }}</span>
                      <button class="tag-remove" type="button" @click="removeAutoLabelTag(tag.id)">×</button>
                    </div>
                  </template>
                  <div v-else class="empty-text">请从下方点选标签，指导AI识别方向</div>
                </div>

                <div v-for="scene in scenes" :key="scene.id" class="scene-block">
                  <div class="scene-title">{{ scene.name }}</div>
                  <div class="scene-tags">
                    <button
                      v-for="tag in scene.tags"
                      :key="tag.id"
                      type="button"
                      class="tag-chip scene-chip"
                      :class="{ active: autoLabelKeywordIds.includes(tag.id) }"
                      :style="{ backgroundColor: tag.color, color: '#fff' }"
                      @click="toggleAutoLabelTag(tag)"
                    >
                      <span>{{ tag.name }}</span>
                      <span v-if="autoLabelKeywordIds.includes(tag.id)" class="tag-remove small">×</span>
                    </button>
                  </div>
                </div>
                
                <div v-if="scenes.length === 0" class="empty-text" style="margin-top: 10px;">
                  暂无可用标签，请先去标注页面创建标签。
                </div>
              </div>

              <div class="dialog-remark-box">
                提示：即将对 <strong>{{ selectedFileIds.length }}</strong> 张图片执行批量智能识别。
              </div>
            </div>

            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="autoLabelVisible = false">取消</button>
              <button 
                class="dialog-btn primary" 
                type="button" 
                :disabled="autoLabelMode === 'keyword' && autoLabelKeywordIds.length === 0"
                @click="confirmAutoLabel"
              >
                确定开始
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
              <input v-model="renameValue" class="dialog-input" placeholder="请输入项目名" />
              <div v-if="renameError" class="dialog-error">{{ renameError }}</div>
            </div>
            <div class="dialog-footer">
              <button class="dialog-btn secondary" @click="closeRenameDialog">取消</button>
              <button class="dialog-btn primary" @click="confirmRename">确定</button>
            </div>
          </div>
        </div>
      </transition>

      <transition name="preview-fade">
        <div v-if="previewVisible" class="preview-mask" @click="closePreview">
          <div class="preview-panel" @click.stop>
            <button class="preview-close-btn" @click="closePreview">×</button>
            <div class="preview-content">
              <img :src="previewImageUrl" class="preview-image" />
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
              <div class="dialog-title">工作设置</div>
              <button class="work-dialog-close" @click="closeWorkDialog">×</button>
            </div>
           
            <div class="dialog-body work-dialog-body">
              <div class="work-file-summary">当前文件：<span>{{ currentWorkFile?.name }}</span></div>
              <div class="mode-row">
                <label class="radio-item" @click="workForm.mode = 'keyword'">
                  <span class="radio-dot" :class="{ active: workForm.mode === 'keyword' }"></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'keyword' }">关键词模型</span>
                </label>
                <label class="radio-item" @click="workForm.mode = 'nonKeyword'">
                  <span class="radio-dot" :class="{ active: workForm.mode === 'nonKeyword' }"></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'nonKeyword' }">非关键词模型</span>
                </label>
              </div>
              <div v-if="workForm.mode === 'keyword'" class="tag-panel">
                <div class="selected-title">已选择的标签</div>
                <div class="selected-box">
                  <div v-for="tag in workSelectedTags" :key="tag.id" class="tag-chip selected" :style="{ backgroundColor: tag.color, color: '#fff' }">
                    {{ tag.name }} <button class="tag-remove" @click="removeWorkTag(tag.id)">×</button>
                  </div>
                  <div v-if="!workSelectedTags.length" class="empty-text">请选择下方标签</div>
                </div>
                <div v-for="scene in scenes" :key="scene.id" class="scene-block">
                  <div class="scene-title">{{ scene.name }}</div>
                  <div class="scene-tags">
                    <button v-for="tag in scene.tags" :key="tag.id" class="tag-chip scene-chip" :class="{ active: isWorkSelected(tag.id) }" :style="{ backgroundColor: tag.color, color: '#fff' }" @click="toggleWorkTag(tag)">
                      {{ tag.name }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="dialog-footer">
              <button class="dialog-btn secondary" @click="closeWorkDialog">取消</button>
              <button class="dialog-btn primary" @click="confirmWorkDialog">确定</button>
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

import { useRouter } from 'vue-router' // 👈 新增引入


const router = useRouter() // 👈 实例化 router
const workLoading = ref(false) // 👈 控制工作弹窗确认按钮的 loading 状态
const STORAGE_KEY = 'image-cap-projects-v1'

// --- 基础状态 ---
const projectList = ref([])
const currentProjectId = ref(null)
const currentFolderId = ref(null)
const hoveredProjectId = ref(null)
const openedProjectMenuId = ref(null)
const searchKeyword = ref('')
const sortType = ref('created_desc')

// --- 获取真实的模型训练库 ---
const trainingStatus = ref({
  current_model: '',
  local_models: [],
  cloud_models: []
})

const checkTrainingStatus = async () => {
  try {
    const res = await fetch('/api/training/status')
    const data = await res.json()
    if (data.local_models) {
      trainingStatus.value = data
      // 默认选中当前正在使用的模型，如果没有则选列表第一个
      if (data.current_model) {
        autoLabelModel.value = data.current_model
      } else if (data.local_models.length > 0) {
        autoLabelModel.value = data.local_models[0].name
      }
    }
  } catch (e) {
    console.error('获取训练模型库失败:', e)
  }
}

// --- 从后端获取真实的动态标签库 ---
const scenes = ref([])

const loadSavedLabels = async () => {
  try {
    const response = await fetch('/api/labels')
    const data = await response.json()
    
    if (data.labels && data.labels.length > 0) {
      // 按照 category 进行分组，如果没有分类则归入“默认标签库”
      const grouped = {}
      data.labels.forEach(label => {
        const catName = label.category || '默认标签库'
        if (!grouped[catName]) {
          grouped[catName] = { id: catName, name: catName, tags: [] }
        }
        grouped[catName].tags.push({
          id: label.name, // 使用 name 作为唯一标识，方便传给后端
          name: label.name,
          color: label.color || '#45b8cb'
        })
      })
      scenes.value = Object.values(grouped)
    }
  } catch (error) {
    console.error('获取标签库失败:', error)
  }
}

// --- 批量逻辑状态 ---
const selectedFileIds = ref([])
const autoLabelVisible = ref(false)
const autoLabelModel = ref('yolov8n')
const autoLabelMode = ref('all') // 'all' | 'keyword'
const autoLabelKeywordIds = ref([])

// --- 弹窗与表单 ---
const renameVisible = ref(false)
const renameProjectId = ref(null)
const renameValue = ref('')
const previewVisible = ref(false)
const previewImageUrl = ref('')
const previewFileName = ref('')
const workVisible = ref(false)
const currentWorkFileId = ref(null)
const workForm = reactive({ mode: 'keyword', selectedTagIds: [] })
const previewUrlMap = new Map()

// --- 计算属性 ---
const currentProject = computed(() => projectList.value.find(p => p.id === currentProjectId.value) || null)
const currentFolder = computed(() => {
  if (!currentProject.value || !currentFolderId.value) return null
  return currentProject.value.folders.find(f => f.id === currentFolderId.value) || null
})

const isAllSelected = computed(() => {
  if (!currentFolder.value || currentFolder.value.files.length === 0) return false
  return selectedFileIds.value.length === currentFolder.value.files.length
})

const filteredProjectList = computed(() => {
  let list = [...projectList.value]
  const kw = searchKeyword.value.trim().toLowerCase()
  if (kw) list = list.filter(p => p.projectName.toLowerCase().includes(kw))
  const sorts = {
    created_desc: (a, b) => b.createdAt - a.createdAt,
    created_asc: (a, b) => a.createdAt - b.createdAt,
    name_asc: (a, b) => a.projectName.localeCompare(b.projectName, 'zh-CN'),
    name_desc: (a, b) => b.projectName.localeCompare(a.projectName, 'zh-CN')
  }
  return list.sort(sorts[sortType.value])
})

const currentWorkFile = computed(() => {
  if (!currentProject.value || !currentWorkFileId.value) return null
  for (const f of currentProject.value.folders) {
    const file = f.files.find(item => item.id === currentWorkFileId.value)
    if (file) return file
  }
  return null
})

const allTags = computed(() => scenes.value.flatMap(s => s.tags))

const workSelectedTags = computed(() => {
  return allTags.value.filter(t => workForm.selectedTagIds.includes(t.id))
})

const autoLabelSelectedTags = computed(() => {
  return allTags.value.filter(t => autoLabelKeywordIds.value.includes(t.id))
})

// --- 批量操作方法 ---
const toggleFileSelection = (id) => {
  const index = selectedFileIds.value.indexOf(id)
  index > -1 ? selectedFileIds.value.splice(index, 1) : selectedFileIds.value.push(id)
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedFileIds.value = []
  } else {
    selectedFileIds.value = currentFolder.value.files.map(f => f.id)
  }
}

// 自动标注相关
const openAutoLabelDialog = () => { 
  autoLabelVisible.value = true 
}

const toggleAutoLabelTag = (tag) => {
  const i = autoLabelKeywordIds.value.indexOf(tag.id)
  i > -1 ? autoLabelKeywordIds.value.splice(i, 1) : autoLabelKeywordIds.value.push(tag.id)
}

const removeAutoLabelTag = (id) => {
  autoLabelKeywordIds.value = autoLabelKeywordIds.value.filter(i => i !== id)
}

const confirmAutoLabel = () => {
  const selectedKeywordNames = autoLabelSelectedTags.value.map(t => t.name)
  
  console.log('--- 批量预标注提交 ---')
  console.log('图片 IDs:', selectedFileIds.value)
  console.log('目标模型:', autoLabelModel.value)
  console.log('过滤模式:', autoLabelMode.value)
  console.log('指定关键词:', selectedKeywordNames)
  
  // 供你之后接入真实后端 API 使用
  const payload = {
    image_ids: selectedFileIds.value,
    model: autoLabelModel.value,
    keywords: autoLabelMode.value === 'keyword' ? selectedKeywordNames : []
  }

  alert(`标注任务已发送:\n数量: ${selectedFileIds.value.length}\n模型: ${autoLabelModel.value}\n模式: ${autoLabelMode.value === 'all' ? '全部目标' : selectedKeywordNames.join(', ')}`)
  
  autoLabelVisible.value = false
  selectedFileIds.value = [] // 提交后清空选中状态
}

// --- 基础导航与持久化 ---
const enterProject = (p) => { currentProjectId.value = p.id; currentFolderId.value = null }
const backToProjectList = () => { currentProjectId.value = null }
const enterFolder = (f) => { currentFolderId.value = f.id }
const backToFolderList = () => { currentFolderId.value = null }

const isImageFile = (f) => f.type?.startsWith('image/')
const getFilePreviewUrl = (file) => {
  if (!isImageFile(file) || !file.file) return ''
  if (previewUrlMap.has(file.id)) return previewUrlMap.get(file.id)
  const url = URL.createObjectURL(file.file); previewUrlMap.set(file.id, url); return url
}

const previewFile = (file) => {
  if (!isImageFile(file) || !file.file) return
  previewImageUrl.value = URL.createObjectURL(file.file)
  previewFileName.value = file.name; previewVisible.value = true
}

const closePreview = () => {
  previewVisible.value = false; if (previewImageUrl.value) URL.revokeObjectURL(previewImageUrl.value)
}

const persist = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(projectList.value))
watch(projectList, persist, { deep: true })

// 防止跨目录误操作，目录改变时清空选中
watch([currentProjectId, currentFolderId], () => { selectedFileIds.value = [] })

onMounted(() => {
  // 加载项目数据
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw) projectList.value = JSON.parse(raw)
  window.addEventListener('click', () => openedProjectMenuId.value = null)
  
  // 初始化加载外部数据 (模型和标签)
  checkTrainingStatus()
  loadSavedLabels()
})

onBeforeUnmount(() => {
  if (previewImageUrl.value) {
    URL.revokeObjectURL(previewImageUrl.value)
  }
  previewUrlMap.forEach((url) => URL.revokeObjectURL(url))
  previewUrlMap.clear()
  window.removeEventListener('click', () => openedProjectMenuId.value = null)
})

// 其他逻辑
const handleCreateProject = (data) => { projectList.value.push({ ...data, createdAt: Date.now() }) }
const toggleProjectMenu = (id) => { openedProjectMenuId.value = openedProjectMenuId.value === id ? null : id }
const formatDate = (ts) => ts ? new Date(ts).toLocaleDateString() : ''
const isWorkSelected = (id) => workForm.selectedTagIds.includes(id)
const toggleWorkTag = (tag) => {
  const i = workForm.selectedTagIds.indexOf(tag.id)
  i > -1 ? workForm.selectedTagIds.splice(i, 1) : workForm.selectedTagIds.push(tag.id)
}
const removeWorkTag = (id) => { workForm.selectedTagIds = workForm.selectedTagIds.filter(i => i !== id) }
const handleWork = (file) => { currentWorkFileId.value = file.id; workVisible.value = true }
const closeWorkDialog = () => { workVisible.value = false }
const confirmWorkDialog = async () => {
  if (!currentProject.value || !currentWorkFile.value) return

  // 1. 获取本地文件对象
  const fileObj = currentWorkFile.value.file
  if (!fileObj) {
    alert("无法获取图片文件，请确保是从本地上传的图片。")
    return
  }

  // 2. 更新本地项目模式状态 (保留你原有的逻辑)
  currentProject.value.mode = workForm.mode
  if (workForm.mode === 'nonKeyword') {
    currentProject.value.selectedTagIds = []
    currentProject.value.selectedTags = []
  } else {
    currentProject.value.selectedTagIds = [...workForm.selectedTagIds]
    currentProject.value.selectedTags = [...workSelectedTags.value]
  }

  // 3. 准备调用后端预测接口
  workLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', fileObj)

    // 如果是关键词模型且选了关键词，把关键词传给后端过滤
    if (workForm.mode === 'keyword' && workSelectedTags.value.length > 0) {
      const keywordNames = workSelectedTags.value.map(t => t.name).join(',')
      formData.append('keywords', keywordNames)
    }

    console.log("🚀 开始调用 predict 接口...", {
      mode: workForm.mode,
      fileName: fileObj.name
    })

    // 4. 调用主预测接口
    const response = await fetch('/api/predict', {
      method: 'POST',
      body: formData
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || '预测失败')
    }

    console.log("✅ 预测成功, task_id:", data.task_id)

    // 5. 成功后，关闭弹窗并携带 task_id 跳转到标注页面
    closeWorkDialog()
    
    // 跳转到 AnnotateView，路由参数会自动触发那边的 restoreTask 逻辑
    router.push(`/app/annotate?task=${data.task_id}`)

  } catch (error) {
    console.error("预测请求出错:", error)
    alert("处理失败：" + error.message)
  } finally {
    workLoading.value = false
  }
}
const openRenameDialog = (project) => { openedProjectMenuId.value = null; renameProjectId.value = project.id; renameValue.value = project.projectName; renameVisible.value = true }
const closeRenameDialog = () => { renameVisible.value = false; renameProjectId.value = null; renameValue.value = '' }
const confirmRename = () => {
  const target = projectList.value.find((item) => item.id === renameProjectId.value)
  if (target) target.projectName = renameValue.value.trim()
  closeRenameDialog()
}
const handleDeleteFromMenu = (projectId) => {
  openedProjectMenuId.value = null
  projectList.value = projectList.value.filter((item) => item.id !== projectId)
  if (currentProjectId.value === projectId) backToProjectList()
}
</script>

<style scoped>
/* --- 新增：批量标注工具栏 --- */
.batch-action-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #f0f9fa;
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

.batch-label-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

/* --- 图片卡片选中样式 --- */
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

.dialog-remark-box {
  margin-top: 12px;
  font-size: 13px;
  color: #4b5563;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 4px solid #45b8cb;
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