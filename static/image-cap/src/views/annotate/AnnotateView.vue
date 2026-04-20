<template>
  <div class="annotation-workspace">

    <aside class="toolbar-panel">
   <section class="tool-section model-section-v2" :class="{ collapsed: collapsedSections.model }">
  <div class="section-header-v2" @click="collapsedSections.model = !collapsedSections.model">
    <div class="header-main">
      <span class="header-icon">🤖</span>
      <h3 class="header-title">
        AI 模型
        <span v-if="currentModel" class="status-badge active">
          运行中
        </span>
        <span v-else class="status-badge inactive">
          未加载
        </span>
      </h3>
    </div>
    <span class="collapse-arrow" :class="{ collapsed: collapsedSections.model }">▼</span>
  </div>

  <div class="model-content-v2" v-show="!collapsedSections.model">
    <!-- 当前模型卡片 -->
    <div v-if="currentModel" class="current-model-card-v2">
      <div class="model-badge" :style="getModelBadgeStyle(currentModel)">
        {{ currentModel.charAt(0).toUpperCase() }}
      </div>
      <div class="model-details">
        <div class="model-name-row">
          <span class="model-name-text">{{ currentModel }}</span>
          <span class="model-tag">{{ getModelType(currentModel) }}</span>
        </div>
      </div>
    </div>
    <div v-else class="current-model-card-v2 empty">
      <div class="model-badge" style="background: linear-gradient(135deg, #999 0%, #666 100%)">?</div>
      <div class="model-details">
        <span class="model-name-text">未选择模型</span>
      </div>
    </div>

    <!-- 模型选择器 - 使用 modelList -->
    <div v-if="modelList?.length" class="model-selector">
      <div class="selector-header">
        <span class="selector-label">切换模型</span>
        <span class="model-count">{{ modelList.length }} 个可用</span>
      </div>
      <div class="model-options">
        <div
          v-for="model in modelList"
          :key="model.name"
          class="model-option"
          :class="{ active: currentModel === model.name }"
          @click="switchModel(model)"
        >
          <div class="option-indicator">
            <div class="radio-circle" :class="{ checked: currentModel === model.name }">
              <div v-if="currentModel === model.name" class="radio-inner"></div>
            </div>
          </div>
          <div class="option-content">
            <div class="option-name">{{ model.name }}</div>
            <div class="option-meta">
              <span class="meta-badge">{{ model.source || '本地' }}</span>
              <span v-if="currentModel === model.name" class="current-mark">当前使用</span>
            </div>
          </div>
          <div v-if="currentModel !== model.name" class="option-action">
            <span class="switch-hint">点击切换</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-model-v2">
      <div class="empty-icon">📭</div>
      <div class="empty-title">暂无可用模型</div>
      <div class="empty-desc">请添加模型文件</div>
    </div>
  </div>
</section>

            <section class="tool-section task-section" :class="{ collapsed: collapsedSections.task }">
        <div class="section-header" @click="collapsedSections.task = !collapsedSections.task">
          <h3 class="section-title">🎯 任务管理</h3>
          <span class="collapse-btn" :class="{ collapsed: collapsedSections.task }">▼</span>
        </div>
        <div class="section-content" v-show="!collapsedSections.task">
          <div v-if="totalTasks > 0" class="task-navigator">
            <div class="navigator-header">
              <span class="task-counter">任务进度: {{ taskNavigatorText }}</span>
              <span v-if="taskList[currentTaskIndex]?.filename" class="task-filename">
                {{ taskList[currentTaskIndex].filename }}
              </span>
            </div>

            <div class="navigator-buttons">
              <button
                @click="goToPrevTask"
                class="btn btn-secondary btn-small"
                :disabled="!canGoPrev || submitLoading"
                title="上一个任务 (Alt+←)"
              >
                ⬅️ 上一个
              </button>

              <button
                @click="goToNextTask"
                class="btn btn-secondary btn-small"
                :disabled="!canGoNext || submitLoading"
                title="下一个任务 (Alt+→)"
              >
                下一个 ➡️
              </button>
            </div>

            <div class="navigator-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${((currentTaskIndex + 1) / totalTasks) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div v-if="store.currentTaskId" class="task-info">
            <div class="task-item">
              <span class="task-label">任务ID:</span>
              <span class="task-value">{{ store.currentTaskId }}</span>
            </div>
            <div class="task-item">
              <span class="task-label">项目:</span>
              <span class="task-value">
                {{
                  store.currentProjectName || route.query.projectName || routeProjectId || '未指定'
                }}
              </span>
            </div>
            <div class="task-item">
              <span class="task-label">状态:</span>
              <span
                class="task-value"
                :style="{ color: getStatusColor(taskList[currentTaskIndex]?.status) }"
              >
                {{ getStatusText(taskList[currentTaskIndex]?.status) }}
              </span>
            </div>
          </div>

          <div v-else class="task-empty">
            <div class="empty-icon">📋</div>
            <p>暂无任务</p>
          </div>

          <div v-if="taskError" class="message error">⚠️ {{ taskError }}</div>
          <div v-if="taskSuccess" class="message success">✅ {{ taskSuccess }}</div>


<button
  v-if="totalTasks === 0"
  @click="loadNextTask(routeProjectId.value)"
  class="btn btn-primary"
  :disabled="taskLoading || submitLoading"
>
  {{ taskLoading ? '⏳ 获取中...' : '🎯 获取新任务' }}
</button>

          <button
            @click="handleCustomSubmit()"
            class="btn btn-success"
            :disabled="!store.currentTaskId || submitLoading || store.annotations.length === 0"
          >
            {{ submitLoading ? '⏳ 提交中...' : '✅ 提交并继续' }}
          </button>

          <button
            @click="saveDraftHandler()"
            class="btn btn-secondary"
            :disabled="!store.currentTaskId || store.annotations.length === 0"
          >
            💾 保存草稿
          </button>

          <button @click="backToProject" class="btn btn-secondary">📁 返回项目</button>

          <button @click="abandonTask()" class="btn btn-danger" :disabled="!store.currentTaskId">
            ❌ 放弃任务
          </button>
        </div>
      </section>

      <section class="tool-section" :class="{ collapsed: collapsedSections.image }">
        <div class="section-header" @click="collapsedSections.image = !collapsedSections.image">
          <h3 class="section-title">📷 图片操作</h3>
          <span class="collapse-btn">▼</span>
        </div>
        <div class="section-content">
          <button @click="loadTestImage()" class="btn btn-primary">加载测试图片</button>
          <input
            type="file"
            ref="fileInput"
            @change="handleFileUpload"
            accept="image/*"
            style="display: none"
          />
          <button @click="$refs.fileInput.click()" class="btn btn-secondary">上传本地图片</button>
          <div class="divider"></div>
          <button
            @click="openSmartAnnotateDialog()"
            class="btn btn-success"
            :disabled="!imageObj || predicting"
          >
            {{ predicting ? '⏳ 识别中...' : '🤖 智能预标注' }}
          </button>
        </div>
      </section>

      <section class="tool-section" :class="{ collapsed: collapsedSections.zoom }">
        <div class="section-header" @click="collapsedSections.zoom = !collapsedSections.zoom">
          <h3 class="section-title">🔍 视图控制</h3>
          <span class="collapse-btn">▼</span>
        </div>
        <div class="section-content">
          <div class="zoom-controls">
            <button @click="zoomOut()" class="btn btn-icon" title="缩小">➖</button>
            <span class="zoom-value">{{ Math.round(zoomScale * 100) }}%</span>
            <button @click="zoomIn()" class="btn btn-icon" title="放大">➕</button>
            <button @click="resetZoom()" class="btn btn-secondary btn-small" title="重置">⟲</button>
          </div>

          <div
            class="pan-controls"
            style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e8e8e8"
          >
            <div class="pan-info" style="font-size: 12px; color: #666; margin-bottom: 8px">
              📍 位置: X: {{ Math.round(stageX) }}, Y: {{ Math.round(stageY) }}
            </div>
            <div class="pan-buttons" style="display: flex; gap: 8px">
              <button
                @click="resetPan()"
                class="btn btn-secondary btn-small"
                style="flex: 1"
                title="重置位置"
              >
                🎯 重置位置
              </button>
              <button
                @click="centerImage()"
                class="btn btn-primary btn-small"
                style="flex: 1"
                title="居中图片"
              >
                ⭕ 居中
              </button>
            </div>
            <div class="pan-hint" style="font-size: 11px; color: #999; margin-top: 8px">
              💡 按住 <kbd>空格</kbd> + 拖拽 或 <kbd>中键</kbd> 拖拽移动图片
            </div>
          </div>

          <div class="divider"></div>
          <button @click="fitToScreen()" class="btn btn-primary btn-small">适应屏幕</button>
          <button @click="actualSize()" class="btn btn-secondary btn-small">实际大小</button>
          <div class="zoom-hint">💡 按住 Ctrl + 滚轮缩放</div>
        </div>
      </section>

      <transition name="fade">
        <section
          class="tool-section selected-annotation-section"
          v-if="selectedAnnotation"
          :class="{ collapsed: collapsedSections.selected }"
        >
          <div
            class="section-header"
            @click="collapsedSections.selected = !collapsedSections.selected"
          >
            <h3 class="section-title">🎯 选中标注</h3>
            <span class="collapse-btn">▼</span>
          </div>
          <div class="section-content">
            <div class="selected-annotation-info">
              <div class="info-row">
                <span class="info-label">标签名称：</span>
                <span
                  class="info-value"
                  :style="{
                    color: selectedAnnotation.color || labelColorMap.get(selectedAnnotation.label),
                  }"
                >
                  <span
                    class="color-dot"
                    :style="{
                      backgroundColor:
                        selectedAnnotation.color || labelColorMap.get(selectedAnnotation.label),
                    }"
                  ></span>
                  <strong>{{ selectedAnnotation.label }}</strong>
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">位置坐标：</span>
                <span class="info-value">
                  X: {{ Math.round(selectedAnnotation.x) }}, Y:
                  {{ Math.round(selectedAnnotation.y) }}
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">尺寸大小：</span>
                <span class="info-value">
                  {{ Math.round(selectedAnnotation.width) }} ×
                  {{ Math.round(selectedAnnotation.height) }} px
                </span>
              </div>
              <div class="info-row" v-if="selectedAnnotation.confidence">
                <span class="info-label">置信度：</span>
                <span class="info-value">
                  {{ (selectedAnnotation.confidence * 100).toFixed(1) }}%
                </span>
              </div>
            </div>
          </div>
        </section>
      </transition>

      <section class="tool-section" :class="{ collapsed: collapsedSections.label }">
        <div class="section-header" @click="collapsedSections.label = !collapsedSections.label">
          <h3 class="section-title">🏷️ 标签管理</h3>
          <span class="collapse-btn">▼</span>
        </div>
        <div class="section-content">
          <div v-if="selectedId" class="selected-annotation-editor">
            <div class="editor-title">🎨 快速编辑</div>
            <div class="editor-row">
              <input
                v-model="editingAnnotationLabel"
                placeholder="输入新标签名称"
                class="input-field"
                @keyup.enter="updateSelectedAnnotationLabel"
              />
            </div>
            <div class="editor-row">
              <button @click="updateSelectedAnnotationColor" class="btn btn-small btn-success">
                改色
              </button>
              <button @click="updateSelectedAnnotationLabel" class="btn btn-small btn-primary">
                修改
              </button>
            </div>
            <div class="editor-row">
              <input type="color" v-model="editingAnnotationColor" class="color-picker-full" />
            </div>
          </div>

          <div v-else class="add-label-section">
            <div class="current-label-display">
              <span class="color-dot" :style="{ backgroundColor: selectedColor }"></span>
              <span class="current-label-text">{{ currentLabel }}</span>
            </div>
            <div class="input-group">
              <input
                v-model="newLabel"
                placeholder="新标签名称"
                class="input-field"
                @keyup.enter="addLabel"
              />
              <input type="color" v-model="selectedColor" class="color-picker" />
            </div>
            <button @click="addLabel()" class="btn btn-primary btn-small">➕ 添加标签</button>
          </div>

          <div class="label-stats" v-if="labelColorMap.size > 0">
            <span class="stats-text">
              已管理 <strong>{{ labelColorMap.size }}</strong> 个标签
            </span>
          </div>

          <div class="label-list" v-if="labels.length > 0">
            <div
              v-for="label in labels"
              :key="label.id"
              class="label-item"
              :class="{ active: currentLabel === label.name }"
            >
              <template v-if="editingLabel !== label.id">
                <div class="label-info" @click="currentLabel = label.name">
                  <span
                    class="color-dot"
                    :style="{
                      backgroundColor: labelColorMap.get(label.name) || label.color,
                    }"
                  ></span>
                  {{ label.name }}
                  <span
                    v-if="annotations.filter((ann) => ann.label === label.name).length > 0"
                    class="label-count"
                  >
                    {{ annotations.filter((ann) => ann.label === label.name).length }}
                  </span>
                </div>
                <div class="label-actions">
                  <button class="btn-icon" @click.stop="startEditLabel(label)" title="编辑标签">
                    ✏️
                  </button>
                  <button
                    class="btn-icon btn-danger"
                    @click.stop="removeLabel(label.name)"
                    title="删除标签"
                  >
                    🗑️
                  </button>
                </div>
              </template>
              <template v-else>
                <div class="edit-mode">
                  <input
                    v-model="editLabelName"
                    class="input-field edit-input"
                    placeholder="输入新名称"
                    @keyup.enter="saveLabelEdit(label.name)"
                    @keyup.esc="cancelLabelEdit"
                  />
                  <button
                    class="btn-icon btn-success"
                    @click="saveLabelEdit(label.name)"
                    title="保存"
                  >
                    ✅
                  </button>
                  <button class="btn-icon" @click="cancelLabelEdit" title="取消">❌</button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </section>

      <section class="tool-section" :class="{ collapsed: collapsedSections.stats }">
        <div class="section-header" @click="collapsedSections.stats = !collapsedSections.stats">
          <h3 class="section-title">📊 统计信息</h3>
          <span class="collapse-btn">▼</span>
        </div>
        <div class="section-content">
          <div class="stat-grid">
            <div class="stat-item">
              <span class="stat-label">标注总数：</span>
              <span class="stat-value">{{ annotations.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">当前标签：</span>
              <span class="stat-value current-tag">{{ currentLabel }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="tool-section action-section">
        <button
          @click.stop="handleDeleteAnnotation"
          class="btn btn-danger"
          :disabled="!selectedId || dialogLock"
        >
          🗑️ 删除选中标注
        </button>
        <div class="divider"></div>
      </section>

      <section class="tool-section export-section">
        <button
          @click.stop="clearAll()"
          class="btn btn-danger"
          :disabled="annotations.length === 0"
        >
          清除所有标注
        </button>
        <button
          @click.stop="exportAnnotations()"
          class="btn btn-success"
          :disabled="annotations.length === 0"
        >
          💾 导出JSON
        </button>
        <button
          @click.stop="exportForYOLO"
          class="btn btn-success"
          :disabled="annotations.length === 0"
        >
          📦 导出YOLO
        </button>
      </section>
    </aside>

    <main class="canvas-container" ref="canvasContainer">
      <div v-if="imageObj" class="canvas-wrapper" :class="{ panning: isSpacePressed || isPanning }">
        <v-stage
          ref="stage"
          :config="scaledStageConfig"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp(currentLabel)"
          @click="handleStageClick"
        >
          <v-layer ref="layer">
            <v-image :config="{ ...scaledImageConfig, name: 'background-image' }" />
            <v-rect v-if="isDrawing && drawingRect" :config="getDrawingRectConfig()" />
            <v-rect
              v-for="ann in annotations"
              :key="ann.id"
              :config="getRectConfig(ann)"
              @click="(e) => selectAnnotation(e, ann.id)"
              @dragend="(e) => handleRectDragEnd(e, ann.id)"
              @dragmove="() => handleRectDragMove(ann.id)"
            />
            <v-text
              v-for="ann in annotations"
              :key="`label-${ann.id}-${dragTick.value}`"
              :config="getTextConfig(ann)"
            />
            <v-transformer
              ref="transformer"
              :config="transformerConfig"
              @transformstart="handleTransformStart"
              @transformend="(e) => handleTransformEnd(e, selectedId)"
            />
          </v-layer>
        </v-stage>
      </div>
      <div v-else class="empty-state">
        <div class="empty-icon">📷</div>
        <p>请加载图片开始标注</p>
        <button @click="loadTestImage()" class="btn btn-primary" style="margin-top: 16px">
          加载测试图片
        </button>
      </div>
    </main>
  </div>

  <teleport to="body">
    <transition name="preview-fade">
      <div v-if="smartAnnotateVisible" class="dialog-mask" @click="smartAnnotateVisible = false">
        <div class="dialog-panel work-dialog-panel" @click.stop>
          <div class="work-dialog-header">
            <div class="dialog-title">智能预标注</div>
            <button class="work-dialog-close" type="button" @click="smartAnnotateVisible = false">
              ×
            </button>
          </div>

          <div class="dialog-body work-dialog-body">
            <div class="work-file-summary">
              {{ smartAnnotateSummaryText }}
            </div>

            <div class="mode-row">
              <label class="radio-item" @click="smartAnnotateMode = 'keyword'">
                <span class="radio-dot" :class="{ active: smartAnnotateMode === 'keyword' }"></span>
                <span class="radio-text" :class="{ strong: smartAnnotateMode === 'keyword' }">
                  关键词模型
                </span>
              </label>

              <label class="radio-item" @click="smartAnnotateMode = 'nonKeyword'">
                <span
                  class="radio-dot"
                  :class="{ active: smartAnnotateMode === 'nonKeyword' }"
                ></span>
                <span class="radio-text" :class="{ strong: smartAnnotateMode === 'nonKeyword' }">
                  非关键词模型
                </span>
              </label>
            </div>

            <div v-if="smartAnnotateMode === 'keyword'" class="tag-panel">
              <div class="selected-title">已选择的标签</div>

              <div class="selected-box">
                <template v-if="selectedSmartKeywords.length">
                  <div
                    v-for="tag in selectedSmartKeywords"
                    :key="tag"
                    class="tag-chip selected"
                    :style="{ backgroundColor: labelColorMap.get(tag) || '#f56c6c' }"
                  >
                    <span>{{ tag }}</span>
                    <button class="tag-remove" type="button" @click="removeSmartKeyword(tag)">
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
                    :class="{ active: selectedSmartKeywords.includes(tag.name) }"
                    :style="{ backgroundColor: tag.color }"
                    @click="toggleSmartKeyword(tag.name)"
                  >
                    <span>{{ tag.name }}</span>
                    <span v-if="selectedSmartKeywords.includes(tag.name)" class="tag-remove small">
                      ×
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="dialog-footer">
            <button
              class="dialog-btn secondary"
              type="button"
              @click="smartAnnotateVisible = false"
            >
              取消
            </button>
            <button
              class="dialog-btn primary"
              type="button"
              :disabled="smartAnnotateMode === 'keyword' && selectedSmartKeywords.length === 0"
              @click="executeSmartAnnotation"
            >
              确定开始
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAnnotationStore } from '@/stores/annotation'
import { useColorManager } from '@/composables/useColorManager'
import { useCanvasEvents } from '@/composables/useCanvasEvents'
import { useTaskFlow } from '@/composables/useTaskFlow'
import { useAnnotationApi } from '@/composables/useAnnotationApi'
import { confirmDialog, promptDialog, alertDialog } from '@/composables/useDialog'
import { supabase } from '@/supabase'
import request from '@/api/request'
import { useRouter, useRoute } from 'vue-router'

const route = useRoute()
const router = useRouter()
const store = useAnnotationStore()

const routeProjectId = computed(() =>
  typeof route.query.projectId === 'string' ? route.query.projectId : ''
)
const routeTaskId = computed(() => (typeof route.query.task === 'string' ? route.query.task : ''))
const routeBatchSize = computed(() => {
  const raw = typeof route.query.batchSize === 'string' ? Number(route.query.batchSize) : 0
  return Number.isFinite(raw) ? raw : 0
})

const imageObj = ref(null)
const fileInput = ref(null)
const transformer = ref(null)
const layer = ref(null)
const canvasContainer = ref(null)
const stage = ref(null)
const newLabel = ref('')
const selectedColor = ref('#ff0000')
const currentLabel = ref('object')
const collapsedSections = reactive({
  image: true,
  label: true,
  stats: true,
  selected: true,
  zoom: true,
  model:true,
  task:true,
})

const editingLabel = ref(null)
const editLabelName = ref('')
const editingOriginalColor = ref('')
const editingAnnotationLabel = ref('')
const editingAnnotationColor = ref('#ff0000')
const dialogLock = ref(false)

const zoomScale = ref(1)
const MIN_ZOOM = 0.1
const MAX_ZOOM = 5
const ZOOM_STEP = 0.1

const baseContainerSize = computed(() => {
  if (!canvasContainer.value || !imageObj.value) {
    return { width: 800, height: 600, scale: 1 }
  }
  const container = canvasContainer.value
  const padding = 40
  const maxWidth = container.clientWidth - padding
  const maxHeight = container.clientHeight - padding

  const imgWidth = imageObj.value.width
  const imgHeight = imageObj.value.height

  const scale = Math.min(maxWidth / imgWidth, maxHeight / imgHeight)

  return {
    width: imgWidth * scale,
    height: imgHeight * scale,
    scale,
  }
})

const containerSize = computed(() => {
  const base = baseContainerSize.value
  return {
    width: base.width * zoomScale.value,
    height: base.height * zoomScale.value,
    scale: base.scale * zoomScale.value,
  }
})

const scaledStageConfig = computed(() => {
  const base = baseContainerSize.value
  return {
    width: base.width * zoomScale.value,
    height: base.height * zoomScale.value,
    scaleX: 1,
    scaleY: 1,
    x: 0,
    y: 0,
  }
})

watch(currentLabel, (label) => {
  selectedColor.value = labelColorMap.get(label) || '#ff0000'
})

const drawingColor = computed(() => labelColorMap.get(currentLabel.value) || '#ff0000')
const annotations = computed(() => store.annotations || [])
const selectedId = computed(() => store.selectedId)

const selectedAnnotation = computed(() => {
  return annotations.value.find((a) => a.id === selectedId.value)
})

const zoomIn = () => {
  if (zoomScale.value < MAX_ZOOM) {
    const oldScale = zoomScale.value
    zoomScale.value = Math.min(zoomScale.value + ZOOM_STEP, MAX_ZOOM)

    const base = baseContainerSize.value
    const centerX = base.width / 2
    const centerY = base.height / 2

    stageX.value = centerX - (centerX - stageX.value) * (zoomScale.value / oldScale)
    stageY.value = centerY - (centerY - stageY.value) * (zoomScale.value / oldScale)

    updateZoom()
  }
}

const zoomOut = () => {
  if (zoomScale.value > MIN_ZOOM) {
    const oldScale = zoomScale.value
    zoomScale.value = Math.max(zoomScale.value - ZOOM_STEP, MIN_ZOOM)

    const base = baseContainerSize.value
    const centerX = base.width / 2
    const centerY = base.height / 2

    stageX.value = centerX - (centerX - stageX.value) * (zoomScale.value / oldScale)
    stageY.value = centerY - (centerY - stageY.value) * (zoomScale.value / oldScale)

    updateZoom()
  }
}

const resetZoom = () => {
  zoomScale.value = 1
  updateZoom()
}

const fitToScreen = () => {
  zoomScale.value = 1
  stageX.value = 0
  stageY.value = 0
  updateZoom()
}

const actualSize = () => {
  const baseScale = baseContainerSize.value.scale
  zoomScale.value = 1 / baseScale

  // 获取画布容器尺寸（可视区域）
  const container = canvasContainer.value
  if (!container || !imageObj.value) return

  // 使用容器的实际尺寸（不是 baseContainerSize）
  const containerWidth = container.clientWidth - 40  // 减去 padding
  const containerHeight = container.clientHeight - 40

  // 图片原始尺寸
  const imgWidth = imageObj.value.width
  const imgHeight = imageObj.value.height

  // 计算画布中心
  const canvasCenterX = containerWidth / 2
  const canvasCenterY = containerHeight / 2

  // 计算 stageX/Y，使得图片居中
  // 在基础坐标系中，图片宽度 = imgWidth * baseScale
  // 要让图片中心对准画布中心：
  // (stageX + imgWidth * baseScale / 2) * zoomScale = canvasCenterX
  // stageX = canvasCenterX / zoomScale - imgWidth * baseScale / 2
  stageX.value = canvasCenterX / zoomScale.value - (imgWidth * baseScale) / 2
  stageY.value = canvasCenterY / zoomScale.value - (imgHeight * baseScale) / 2

  updateZoom()
}

const updateZoom = () => {
  dragTick.value++
  if (transformer.value && selectedId.value) {
    nextTick(() => {
      const tr = transformer.value.getNode()
      tr.forceUpdate()
    })
  }
}

const handleWheel = (e) => {
  if (!imageObj.value) return
  if (!e.ctrlKey && !e.metaKey) return

  e.preventDefault()

  const stageNode = stage.value?.getNode()
  if (!stageNode) return

  const oldScale = zoomScale.value
  const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
  const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomScale.value + delta))

  if (newScale !== oldScale) {
    const pointer = stageNode.getPointerPosition()
    if (!pointer) return

    const mouseX = (pointer.x - stageX.value) / oldScale
    const mouseY = (pointer.y - stageY.value) / oldScale

    zoomScale.value = newScale

    stageX.value = pointer.x - mouseX * newScale
    stageY.value = pointer.y - mouseY * newScale

    updateZoom()
  }
}

const smartAnnotateVisible = ref(false)
const smartAnnotateMode = ref('keyword')
const selectedSmartKeywords = ref([])

const scenes = ref([
  {
    id: 1,
    name: '常用标签',
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
    name: '其他标签',
    tags: [
      { id: 6, name: 'horse', color: '#aee9ec' },
      { id: 7, name: 'bird', color: '#f2d562' },
      { id: 8, name: 'sheep', color: '#eea2ca' },
    ],
  },
])

const smartAnnotateSummaryText = computed(() => {
  if (!imageObj.value) return '请先加载图片'
  return `当前图片：${store.currentTaskId || '测试图片'}`
})

const openSmartAnnotateDialog = () => {
  if (!imageObj.value) {
    alert('请先上传或加载图片')
    return
  }

  if (selectedSmartKeywords.value.length === 0 && scenes.value.length > 0) {
    const firstTag = scenes.value[0].tags[0]
    if (firstTag) {
      selectedSmartKeywords.value = [firstTag.name]
    }
  }

  smartAnnotateVisible.value = true
}

const toggleSmartKeyword = (name) => {
  const index = selectedSmartKeywords.value.indexOf(name)
  if (index > -1) {
    selectedSmartKeywords.value.splice(index, 1)
  } else {
    selectedSmartKeywords.value.push(name)
  }
}

const removeSmartKeyword = (name) => {
  const index = selectedSmartKeywords.value.indexOf(name)
  if (index > -1) {
    selectedSmartKeywords.value.splice(index, 1)
  }
}

const executeSmartAnnotation = async () => {
  if (!imageObj.value) return

  smartAnnotateVisible.value = false
  predicting.value = true
  taskError.value = ''
  taskSuccess.value = '🔍 正在进行增量智能识别，请稍候...'

  try {
    const keywords = smartAnnotateMode.value === 'keyword' ? [...selectedSmartKeywords.value] : []

    let data

    if (store.currentTaskId) {
      const response = await fetch(`/api/tasks/${store.currentTaskId}/smart-annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords,
          iou_threshold: 0.5,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '增量预标注失败')
      }

      data = await response.json()
    } else {
      const canvas = document.createElement('canvas')
      canvas.width = imageObj.value.width
      canvas.height = imageObj.value.height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(imageObj.value, 0, 0)

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9))
      const formData = new FormData()
      formData.append('file', blob, 'image.jpg')

      if (keywords.length > 0) {
        formData.append('keywords', JSON.stringify(keywords))
      }

      const response = await fetch('/api/predict', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '预测失败')
      }

      data = await response.json()
    }

    if (!data.success) {
      throw new Error(data.message || '识别失败')
    }

    if (data.annotations && data.annotations.length > 0) {
      // ========== 使用新的统一处理方法 ==========
      const processedNewAnnotations = await processAIAnnotations(data.annotations, 'smart-annotate')

      const currentAnnotations = store.annotations || []
      store.setAnnotations([...currentAnnotations, ...processedNewAnnotations])
      // ========== 结束修改 ==========

      const stats = data.stats || {}
      taskSuccess.value = `🤖 增量识别完成！新增 ${data.annotations.length} 个目标（AI检测到${
        stats.ai_detected || 0
      }个，跳过重复${stats.duplicate_skipped || 0}个）`
      setTimeout(() => (taskSuccess.value = ''), 4000)
      dragTick.value++
    } else {
      const stats = data.stats || {}
      taskSuccess.value = ''
      taskError.value = `⚠️ 未发现新目标（AI检测到${stats.ai_detected || 0}个，全部与已有标注重复）`
      setTimeout(() => (taskError.value = ''), 3000)
    }
  } catch (error) {
    console.error('增量智能标注失败:', error)
    taskError.value = `❌ 智能标注失败: ${error.message}`
    setTimeout(() => (taskError.value = ''), 3000)
  } finally {
    predicting.value = false
  }
}

const { labelColorMap, generateColor, ensureLabelColor, syncLabelsFromMap, labels } =
  useColorManager([
    { id: 1, name: 'person', color: '#ff0000' },
    { id: 2, name: 'car', color: '#0000ff' },
    { id: 3, name: 'dog', color: '#00ff00' },
  ])

const {
  taskLoading,
  submitLoading,
  taskError,
  taskSuccess,
  loadNextTask,
  loadTestImage,
  submitAnnotations,
  saveDraftHandler,
  abandonTask,
  fetchProjectTask,
  restoreTask,
} = useTaskFlow(store, imageObj, labelColorMap)

const {
  isDrawing,
  drawingRect,
  dragTick,
  isPanning,
  stageX,
  stageY,
  isSpacePressed,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  selectAnnotation,
  deleteAnnotation,
  handleRectDragMove,
  handleRectDragEnd,
  handleTransformStart,
  handleTransformEnd,
  handleStageClick,
  resetPan,
  setSpacePressed,
} = useCanvasEvents(
  baseContainerSize,
  selectedColor,
  labelColorMap,
  store,
  transformer,
  layer,
  annotations,
  currentLabel,
  imageObj
)

const { predicting } = useAnnotationApi(
  baseContainerSize,
  store,
  imageObj,
  labelColorMap,
  taskError,
  taskSuccess,
  currentLabel,
  labels,
  ensureLabelColor
)

const loadTaskListFromStorage = async () => {
  const projectId = routeProjectId.value
  if (!projectId) return false

  const savedList = localStorage.getItem(`task_list_${projectId}`)
  const urlBatchSize = parseInt(route.query.batchSize || '0')

  if (savedList) {
    try {
      const parsed = JSON.parse(savedList)
      taskList.value = parsed.tasks || []
      totalTasks.value = taskList.value.length

      if (urlBatchSize > 0 && taskList.value.length < urlBatchSize) {
        console.log(`⚠️ 任务列表不匹配: 缓存${taskList.value.length}个, 期望${urlBatchSize}个`)
        return await loadProjectLabelingTasks(projectId)
      }

      if (parsed.currentIndex !== undefined) {
        currentTaskIndex.value = parsed.currentIndex
      }

      console.log(`📋 从缓存加载任务列表: ${totalTasks.value} 个任务`)
      return true
    } catch (e) {
      console.error('解析任务列表失败:', e)
    }
  }

  return await loadProjectLabelingTasks(projectId)
}

const loadProjectLabelingTasks = async (projectId) => {
  try {
    console.log(`🔄 从后端加载项目所有标注中任务: ${projectId}`)

    const response = await fetch(`/api/projects/${projectId}/all-labeling-tasks`)

    if (!response.ok) {
      console.warn('获取项目所有标注中任务失败，使用当前任务')
      return false
    }

    const data = await response.json()

    if (data.tasks && data.tasks.length > 0) {
      taskList.value = data.tasks
      totalTasks.value = data.tasks.length

      const currentTaskId = routeTaskId.value
      const currentIndex = taskList.value.findIndex((t) => t.task_id === currentTaskId)

      if (currentIndex !== -1) {
        currentTaskIndex.value = currentIndex
      } else {
        currentTaskIndex.value = 0
      }

      localStorage.setItem(
        `task_list_${projectId}`,
        JSON.stringify({
          tasks: taskList.value,
          currentIndex: currentTaskIndex.value,
          projectId,
          projectName: route.query.projectName,
          folderType: 'labeling',
        })
      )

      console.log(`✅ 加载项目所有标注中任务: ${totalTasks.value} 个`)
      return true
    }

    return false
  } catch (error) {
    console.error('加载项目标注中任务失败:', error)
    return false
  }
}

const saveTaskListToStorage = () => {
  const projectId = routeProjectId.value
  if (!projectId || taskList.value.length === 0) return

  localStorage.setItem(
    `task_list_${projectId}`,
    JSON.stringify({
      tasks: taskList.value,
      currentIndex: currentTaskIndex.value,
      projectId,
      projectName: route.query.projectName || store.currentProjectName,
      folderType: route.query.folderType || 'labeling',
    })
  )
}

const updateCurrentTaskIndex = (taskId) => {
  const index = taskList.value.findIndex((t) => t.task_id === taskId)
  if (index !== -1) {
    currentTaskIndex.value = index
    saveTaskListToStorage()
  }
}

const loadTask = async (taskId) => {
  if (!taskId) return false

  try {
    console.log(`📥 加载任务: ${taskId}`)

    if (routeProjectId.value) {
      const loaded = await fetchProjectTask(routeProjectId.value, taskId)
      if (loaded) {
        loadPreAnnotations(taskId)
        updateCurrentTaskIndex(taskId)
        return true
      }
    }

    const restored = await restoreTask(taskId)
    return restored
  } catch (error) {
    console.error('加载任务失败:', error)
    return false
  }
}

const goToPrevTask = async () => {
  if (!canGoPrev.value) {
    taskError.value = '已经是第一个任务了'
    setTimeout(() => (taskError.value = ''), 2000)
    return
  }

  if (store.currentTaskId && store.annotations.length > 0) {
    await saveDraftHandler()
  }

  const prevIndex = currentTaskIndex.value - 1
  const prevTask = taskList.value[prevIndex]

  if (!prevTask) {
    taskError.value = '未找到上一个任务'
    return
  }

  console.log(`⬅️ 导航到上一个任务: ${prevTask.task_id} (${prevIndex + 1}/${totalTasks.value})`)

  await router.replace({
    path: '/app/annotate',
    query: {
      ...route.query,
      task: prevTask.task_id,
      taskIndex: String(prevIndex),
    },
  })

  const loaded = await loadTask(prevTask.task_id)

  if (loaded) {
    taskSuccess.value = `⬅️ 已加载上一个任务 (${prevIndex + 1}/${totalTasks.value})`
    setTimeout(() => (taskSuccess.value = ''), 2000)
  } else {
    taskError.value = '加载上一个任务失败'
  }
}

const goToNextTask = async () => {
  if (!canGoNext.value) {
    taskError.value = '已经是最后一个任务了'
    setTimeout(() => (taskError.value = ''), 2000)
    return
  }

  if (store.currentTaskId && store.annotations.length > 0) {
    await saveDraftHandler()
  }

  const nextIndex = currentTaskIndex.value + 1
  const nextTask = taskList.value[nextIndex]

  if (!nextTask) {
    taskError.value = '未找到下一个任务'
    return
  }

  console.log(`➡️ 导航到下一个任务: ${nextTask.task_id} (${nextIndex + 1}/${totalTasks.value})`)

  await router.replace({
    path: '/app/annotate',
    query: {
      ...route.query,
      task: nextTask.task_id,
      taskIndex: String(nextIndex),
    },
  })

  const loaded = await loadTask(nextTask.task_id)

  if (loaded) {
    taskSuccess.value = `➡️ 已加载下一个任务 (${nextIndex + 1}/${totalTasks.value})`
    setTimeout(() => (taskSuccess.value = ''), 2000)
  } else {
    taskError.value = '加载下一个任务失败'
  }
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待标注',
    labeling: '标注中',
    done: '已完成',
    review: '审核中',
    reviewed: '已审核',
    abandoned: '已放弃',
  }
  return statusMap[status] || status || '未知'
}

const getStatusColor = (status) => {
  const colorMap = {
    pending: '#faad14',
    labeling: '#52c41a',
    done: '#1890ff',
    review: '#722ed1',
    reviewed: '#7c3aed',
    abandoned: '#ff4d4f',
  }
  return colorMap[status] || '#666'
}

const handleCustomSubmit = async () => {
  if (!store.currentTaskId || store.annotations.length === 0) return

  try {
    const submitResult = await submitAnnotations()
    if (submitResult === false) {
      throw new Error('标注提交失败')
    }

    if (routeProjectId.value) {
      try {
        await request.post(`/project/${routeProjectId.value}/move-to-done`, {
          taskId: store.currentTaskId,
        })
      } catch (e) {
        console.warn('调用 move-to-done 接口失败:', e)
      }
    }

    taskSuccess.value = `✅ 任务 ${store.currentTaskId} 提交成功`

    if (canGoNext.value) {
      setTimeout(() => {
        goToNextTask()
      }, 800)
    } else {
      window.alert('该批次已全部标注完成！')
      router.push('/app/project')
    }
  } catch (error) {
    console.error('提交失败:', error)
    taskError.value = '提交失败: ' + error.message
  }
}

const backToProject = () => {
  window.opener?.postMessage('refresh-project', '*')
  router.push('/app/project')
}

const loadNextTaskWithCleanup = async () => {
  const oldTaskId = store.currentTaskId
  await loadNextTask()
  if (oldTaskId && oldTaskId !== store.currentTaskId) {
    clearPreAnnotations(oldTaskId)
  }
}

const currentScale = computed(() => {
  return (baseContainerSize.value?.scale || 1) * zoomScale.value
})

const getDrawingRectConfig = () => {
  if (!drawingRect.value || !baseContainerSize.value) return {}

  const baseScale = baseContainerSize.value.scale || 1

  return {
    x: (drawingRect.value.x * baseScale + stageX.value) * zoomScale.value,
    y: (drawingRect.value.y * baseScale + stageY.value) * zoomScale.value,
    width: drawingRect.value.width * baseScale * zoomScale.value,
    height: drawingRect.value.height * baseScale * zoomScale.value,
    stroke: drawingColor.value,
    strokeWidth: 2 / zoomScale.value,
    fill: 'rgba(0, 0, 0, 0.05)',
    listening: false,
  }
}


// 防抖映射
const pendingLabelSaves = new Map()

const saveLabelToBackend = async (name, color) => {
  const key = `${name}:${color}`
  if (pendingLabelSaves.has(key)) {
    return pendingLabelSaves.get(key)
  }

  const savePromise = (async () => {
    try {
      const response = await fetch('/api/labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          color,
          category: null,
        }),
      })

      if (response.ok) {
        console.log(`✅ 标签 ${name} (${color}) 已保存到后端`)
        return { success: true }
      }

      const errorData = await response.json()
      if (response.status === 409 || errorData.detail?.includes('已存在')) {
        const updateRes = await fetch(`/api/labels/${encodeURIComponent(name)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ color }),
        })

        if (updateRes.ok) {
          console.log(`✅ 标签 ${name} 颜色已更新为 ${color}`)
          return { success: true }
        }
      }

      throw new Error(errorData.detail || '保存失败')
    } catch (error) {
      console.error('保存标签失败:', error)
      throw error
    } finally {
      setTimeout(() => pendingLabelSaves.delete(key), 100)
    }
  })()

  pendingLabelSaves.set(key, savePromise)
  return savePromise
}

/** 统一处理 AI 识别出的新标签 */
const processAIAnnotations = async (annotations, source = 'ai') => {
  if (!annotations || annotations.length === 0) return []

  const newLabelsToSave = []
  const processedAnnotations = []

  for (const ann of annotations) {
    const labelName = ann.label
    if (!labelName) continue

    let labelColor = ann.color
    if (!labelColor) {
      labelColor = labelColorMap.get(labelName) || ensureLabelColor(labelName)
    }

    if (!labelColorMap.has(labelName)) {
      labelColorMap.set(labelName, labelColor)
      newLabelsToSave.push({ name: labelName, color: labelColor })
      console.log(`🆕 发现新标签 [${source}]: ${labelName} -> ${labelColor}`)
    } else if (labelColorMap.get(labelName) !== labelColor) {
      labelColorMap.set(labelName, labelColor)
      newLabelsToSave.push({ name: labelName, color: labelColor })
      console.log(`🎨 更新标签颜色 [${source}]: ${labelName} -> ${labelColor}`)
    }

    processedAnnotations.push({
      ...ann,
      color: labelColor,
      source: ann.source || source,
      isNew: ann.isNew || source === 'ai'
    })
  }

  if (newLabelsToSave.length > 0) {
    console.log(`💾 批量保存 ${newLabelsToSave.length} 个标签到后端:`, newLabelsToSave)
    syncLabelsFromMap()

    const savePromises = newLabelsToSave.map(async (label) => {
      try {
        await saveLabelToBackend(label.name, label.color)
        return { success: true, name: label.name }
      } catch (e) {
        console.error(`❌ 保存标签 ${label.name} 失败:`, e)
        return { success: false, name: label.name, error: e }
      }
    })

    const results = await Promise.allSettled(savePromises)
    const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length
    console.log(`✅ 标签保存完成: ${successCount}/${newLabelsToSave.length} 成功`)
  }

  return processedAnnotations
}
const trainingStatus = ref({
  dataset_ready: false,
  dataset_stats: {},
  local_models: [],
  current_model: '',
  cuda_available: false,
})
const trainingConfig = ref({
  epochs: 100,
  model_size: 'auto',
})
const trainingLoading = ref(false)
const trainingMessage = ref(null)

const checkTrainingStatus = async () => {
  try {
    const res = await fetch('/api/training/status')
    const data = await res.json()
    trainingStatus.value = data
  } catch (e) {
    console.error('获取训练状态失败:', e)
  }
}



const startTraining = async () => {
  trainingLoading.value = true
  trainingMessage.value = null

  try {
    const params = new URLSearchParams({
      epochs: trainingConfig.value.epochs,
      batch: 16,
      model_size: trainingConfig.value.model_size,
      augmentation: true,
    })

    const res = await fetch(`/api/training/start?${params}`, {
      method: 'POST',
    })
    const data = await res.json()

    if (data.success) {
      trainingMessage.value = {
        type: 'success',
        text: `训练已启动！模型: ${data.config.model_size}, 轮数: ${data.config.epochs}`,
      }
      setInterval(checkTrainingStatus, 10000)
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    trainingMessage.value = {
      type: 'error',
      text: '启动失败: ' + e.message,
    }
  } finally {
    trainingLoading.value = false
  }
}



const getRectConfig = (ann) => {
  void dragTick.value
  const { scale: baseScale } = baseContainerSize.value

  const finalColor = labelColorMap.get(ann.label) || ann.color || '#ff0000'
  const isSelected = selectedId.value === ann.id

  return {
    id: ann.id,
    x: (ann.x * baseScale + stageX.value) * zoomScale.value,
    y: (ann.y * baseScale + stageY.value) * zoomScale.value,
    width: ann.width * baseScale * zoomScale.value,
    height: ann.height * baseScale * zoomScale.value,
    stroke: finalColor,
    strokeWidth: isSelected ? 3 / zoomScale.value : 2 / zoomScale.value,
    fill: isSelected ? 'rgba(0, 0, 0, 0.05)' : 'rgba(0,0,0,0)',
    draggable: true,
    name: `rect-${ann.id}`,
    listening: true,
    scaleX: 1,
    scaleY: 1,
    shadowEnabled: isSelected,
    shadowColor: finalColor,
    shadowBlur: 8,
    shadowOpacity: 0.3,
  }
}

const getTextConfig = (ann) => {
  void dragTick.value
  const { scale: baseScale } = baseContainerSize.value

  const finalColor = labelColorMap.get(ann.label) || ann.color || '#ff0000'
  const isSelected = selectedId.value === ann.id

  const confidenceText = ann.confidence ? ` ${(ann.confidence * 100).toFixed(0)}%` : ''
  return {
    x: (ann.x * baseScale + stageX.value) * zoomScale.value,
    y: (ann.y * baseScale + stageY.value - (isSelected ? 28 : 25)) * zoomScale.value,
    text: `${ann.label}${confidenceText}`,
    fontSize: (isSelected ? 16 : 14) / zoomScale.value,
    fill: finalColor,
    fontStyle: 'bold',
    padding: isSelected ? 6 : 5,
    backgroundColor: isSelected ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.9)',
    listening: false,
    name: `text-${ann.id}`,
    opacity: isSelected ? 1 : ann.confidence ? 0.6 + ann.confidence * 0.4 : 1,
    shadowEnabled: isSelected,
    shadowColor: 'rgba(0, 0, 0, 0.3)',
    shadowBlur: 4,
    shadowOffsetY: 2,
  }
}

const scaledImageConfig = computed(() => {
  if (!imageObj.value) return {}
  const { scale: baseScale } = baseContainerSize.value

  return {
    image: imageObj.value,
    x: stageX.value * zoomScale.value,
    y: stageY.value * zoomScale.value,
    width: imageObj.value.width * baseScale * zoomScale.value,
    height: imageObj.value.height * baseScale * zoomScale.value,
  }
})
// 获取模型颜色
const getModelColor = (modelName) => {
  const name = modelName.toLowerCase()
  let gradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'

  if (name.includes('yolo')) {
    gradient = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
  } else if (name.includes('rcnn')) {
    gradient = 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)'
  } else if (name.includes('ssd')) {
    gradient = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
  } else if (name.includes('detr')) {
    gradient = 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)'
  } else if (name.includes('vit')) {
    gradient = 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
  }

  return { background: gradient }
}

// 获取模型类型标签
const getModelType = (modelName) => {
  const name = modelName.toLowerCase()
  if (name.includes('yolo')) return 'YOLO'
  if (name.includes('rcnn')) return 'RCNN'
  if (name.includes('ssd')) return 'SSD'
  if (name.includes('detr')) return 'DETR'
  if (name.includes('vit')) return 'ViT'
  return '本地'
}




const transformerConfig = computed(() => {
  if (!selectedId.value) {
    return { visible: false }
  }

  const ann = annotations.value.find((a) => a.id === selectedId.value)
  const color = ann ? labelColorMap.get(ann.label) : '#409EFF'

  return {
    anchorStroke: color,
    anchorFill: color,
    borderStroke: color,
    borderDash: [5, 5],
    anchorSize: 10 / zoomScale.value,
    rotateEnabled: false,
    keepRatio: false,
    centeredScaling: true,
    visible: true,
    boundBoxFunc: (oldBox, newBox) => {
      const base = baseContainerSize.value
      const maxWidth = base.width * zoomScale.value
      const maxHeight = base.height * zoomScale.value

      if (newBox.x < 0) newBox.x = 0
      if (newBox.y < 0) newBox.y = 0
      if (newBox.x + newBox.width > maxWidth) {
        newBox.width = maxWidth - newBox.x
      }
      if (newBox.y + newBox.height > maxHeight) {
        newBox.height = maxHeight - newBox.y
      }
      return newBox
    },
  }
})

const exportForYOLO = async () => {
  if (annotations.value.length === 0) {
    await alertDialog({
      title: '提示',
      content: '没有标注数据',
      variant: 'info',
    })
    return
  }

  if (!imageObj.value) {
    console.error('无图片对象')
    return
  }

  const imgWidth = imageObj.value.width
  const imgHeight = imageObj.value.height

  const yoloData = annotations.value
    .map((ann) => {
      const classId = labels.value.findIndex((l) => l.name === ann.label)
      const centerX = (ann.x + ann.width / 2) / imgWidth
      const centerY = (ann.y + ann.height / 2) / imgHeight
      const normWidth = ann.width / imgWidth
      const normHeight = ann.height / imgHeight

      return `${classId} ${centerX.toFixed(6)} ${centerY.toFixed(6)} ${normWidth.toFixed(
        6
      )} ${normHeight.toFixed(6)}`
    })
    .join('\n')

  const txtBlob = new Blob([yoloData], { type: 'text/plain' })
  const url = URL.createObjectURL(txtBlob)
  const a = document.createElement('a')
  a.href = url
  a.download = `image_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)

  const classesData = labels.value.map((l, idx) => `${idx} ${l.name}`).join('\n')
  const classesBlob = new Blob([classesData], { type: 'text/plain' })
  const classesUrl = URL.createObjectURL(classesBlob)
  const classesA = document.createElement('a')
  classesA.href = classesUrl
  classesA.download = 'classes.txt'
  classesA.click()
  URL.revokeObjectURL(classesUrl)
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  taskLoading.value = true
  taskError.value = ''

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch('/api/predict', {
      method: 'POST',
      body: formData,
    })

      const data = await response.json()
    console.log('📦 后端返回数据:', data)  // 添加这行

    if (!response.ok) {
      throw new Error(data.detail || '上传失败')
    }

    localStorage.setItem('lastTaskId', data.task_id)
    window.history.replaceState({}, '', `?task=${data.task_id}`)

    store.clearAnnotations()
     // 安全检查：确保有图片 URL
    const imageUrl = data.image_url || data.imageUrl || data.url || data.file_url
    const taskId = data.task_id || data.taskId || data.id || `upload_${Date.now()}`

    if (!imageUrl) {
      console.error('后端返回数据:', data)
      throw new Error('上传成功但未返回图片URL，请检查后端接口')
    }

    store.setCurrentTask({
      id: taskId,
      imageUrl: imageUrl,
      imageStoragePath: data.image_storage_path || data.storage_path || '',
    })

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = imageUrl

    img.onload = async () => {
      imageObj.value = img

      await nextTick()
      dragTick.value++

      setTimeout(() => {
        dragTick.value++
        console.log('📐 图片加载完成，强制刷新画布', {
          containerWidth: canvasContainer.value?.clientWidth,
          containerHeight: canvasContainer.value?.clientHeight,
          imageWidth: img.width,
          imageHeight: img.height,
          computedSize: containerSize.value,
        })
      }, 100)

      // ========== 使用新的统一处理方法 ==========
      if (data.annotations && data.annotations.length > 0) {
        const processedAnnotations = await processAIAnnotations(data.annotations, 'upload-predict')
        store.setAnnotations(processedAnnotations)

        const firstAnnotation = processedAnnotations[0]
        const firstLabel = firstAnnotation.label

        if (!labelColorMap.has(firstLabel)) {
          const color = firstAnnotation.color || ensureLabelColor(firstLabel)
          labelColorMap.set(firstLabel, color)
          await saveLabelToBackend(firstLabel, color)
        }

        currentLabel.value = firstLabel
        selectedColor.value = labelColorMap.get(firstLabel)

        syncLabelsFromMap()
        dragTick.value++

        console.log('🎯 当前标签已自动切换为:', firstLabel, '颜色:', selectedColor.value)
      }
      // ========== 结束修改 ==========

      const stats = data.stats || {}
      taskSuccess.value = `✅ 上传成功，检测到 ${
        stats.final_count || data.annotations?.length || 0
      } 个目标${stats.removed_duplicates > 0 ? `（已去重${stats.removed_duplicates}个）` : ''}`
      setTimeout(() => (taskSuccess.value = ''), 3000)
    }

        img.onerror = () => {
      taskError.value = '❌ 图片加载失败'
      console.error('图片加载失败，URL:', imageUrl, '任务ID:', taskId)
    
    }
  } catch (error) {
    console.error('上传失败:', error)
    taskError.value = `❌ 上传失败: ${error.message}`
  } finally {
    taskLoading.value = false
    event.target.value = ''
  }
}



const addLabel = async () => {
  if (!newLabel.value.trim()) {
    await alertDialog({
      title: '提示',
      content: '请输入标签名称',
      variant: 'info',
    })
    return
  }

  const labelName = newLabel.value.trim()
  const exists = labels.value.some((l) => l.name === labelName)
  if (exists) {
    await alertDialog({
      title: '提示',
      content: '标签已存在',
      variant: 'info',
    })
    return
  }

  const assignedColor = ensureLabelColor(labelName, selectedColor.value)
  syncLabelsFromMap()

  await saveLabelToBackend(labelName, assignedColor)

  currentLabel.value = labelName
  selectedColor.value = assignedColor
  newLabel.value = ''

  dragTick.value++
}

const clearAll = async () => {
  console.log('🔥 [ClearAll] 清除所有标注被触发')
  const result = await confirmDialog({
    title: '确认清除',
    content: '确定清除所有标注吗？此操作不可撤销。',
    variant: 'error',
  })

  if (result.confirmed) {
    store.clearAnnotations()
    if (store.currentTaskId) {
      await supabase.from('drafts').delete().eq('task_id', store.currentTaskId)
    }
  }
}

const exportAnnotations = async () => {
  if (annotations.value.length === 0) {
    await alertDialog({
      title: '提示',
      content: '没有标注数据',
      variant: 'info',
    })
    return
  }

  const data = {
    image: { width: imageObj.value.width, height: imageObj.value.height },
    annotations: annotations.value,
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `annotations_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const handleDeleteAnnotation = async () => {
  console.log('🔥 [Delete] 删除选中标注被触发')

  if (!selectedId.value || dialogLock.value) {
    console.log('🔥 [Delete] 操作被阻止：lock=', dialogLock.value, 'selectedId=', selectedId.value)
    return
  }

  const annotation = annotations.value.find((a) => a.id === selectedId.value)
  if (!annotation) return

  dialogLock.value = true
  console.log('🔥 [Delete] 锁定弹窗')

  try {
    const result = await confirmDialog({
      title: '删除标注',
      content: `确定要删除标注 "${annotation.label}" 吗？此操作无法撤销。`,
      variant: 'error',
    })

    if (result.confirmed) {
      deleteAnnotation(selectedId.value)
      console.log('🔥 [Delete] 删除成功')
    } else {
      console.log('🔥 [Delete] 用户取消删除')
    }
  } catch (error) {
    console.error('🔥 [Delete] 删除过程出错:', error)
  } finally {
    setTimeout(() => {
      dialogLock.value = false
      console.log('🔥 [Delete] 解锁完成')
    }, 300)
  }
}

const handleKeydown = async (e) => {
  if (dialogLock.value) {
    console.log('🔥 [Keydown] 键盘事件被阻止：弹窗锁定中')
    return
  }

  const activeElement = document.activeElement
  const isInInput = activeElement && ['INPUT', 'TEXTAREA'].includes(activeElement.tagName)
  if (isInInput) return

  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId.value) {
    e.preventDefault()
    console.log('🔥 [Keydown] Delete键触发删除')
    await handleDeleteAnnotation()
    return
  }

  if (e.key === 'F2' && selectedId.value) {
    e.preventDefault()
    updateSelectedLabel()
    return
  }

  if (e.key === 'Delete' && e.ctrlKey && annotations.value.length > 0) {
    e.preventDefault()
    clearAll()
    return
  }

  if (e.key === 'Escape' && selectedId.value) {
    e.preventDefault()
    store.selectedId = null
    if (transformer.value) {
      transformer.value.getNode().nodes([])
    }
  }
}

const startEditLabel = (label) => {
  editingLabel.value = label.id
  editLabelName.value = label.name

  let color = label.color
  if (!color) color = labelColorMap.get(label.name)
  if (!color) color = '#ff0000'

  editingOriginalColor.value = color
}

const saveLabelEdit = async (oldName) => {
  const newName = editLabelName.value.trim()

  if (!newName) {
    await alertDialog({ title: '提示', content: '标签名称不能为空', variant: 'error' })
    return
  }

  if (newName === oldName) {
    editingLabel.value = null
    editingOriginalColor.value = ''
    return
  }

  if (labelColorMap.has(newName)) {
    await alertDialog({ title: '提示', content: '标签名称已存在', variant: 'info' })
    return
  }

  let color = editingOriginalColor.value
  if (!color) color = labelColorMap.get(oldName)
  if (!color) {
    const annotation = store.annotations.find((ann) => ann.label === oldName)
    color = annotation?.color
  }
  if (!color) color = '#ff0000'

  try {
    const createRes = await fetch('/api/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newName,
        color,
        category: null,
      }),
    })

    if (!createRes.ok) {
      const errorData = await createRes.json()
      if (errorData.detail?.includes('已存在')) {
        await fetch(`/api/labels/${encodeURIComponent(newName)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ color }),
        })
      } else {
        throw new Error(errorData.detail || '创建新标签失败')
      }
    }

    try {
      await fetch(`/api/labels/${encodeURIComponent(oldName)}`, {
        method: 'DELETE',
      })
    } catch (e) {
      console.log('删除旧标签失败（可能后端没有该记录）:', e)
    }

    labelColorMap.delete(oldName)
    labelColorMap.set(newName, color)

    const oldLabelIndex = labels.value.findIndex((l) => l.name === oldName)
    if (oldLabelIndex !== -1) {
      labels.value[oldLabelIndex] = {
        id: labels.value[oldLabelIndex].id,
        name: newName,
        color,
      }
    } else {
      labels.value.push({
        id: `label_${Date.now()}`,
        name: newName,
        color,
      })
    }

    store.annotations.forEach((ann) => {
      if (ann.label === oldName) {
        ann.label = newName
        ann.color = color
      }
    })

    if (currentLabel.value === oldName) {
      currentLabel.value = newName
      selectedColor.value = color
    }

    dragTick.value++
    editingLabel.value = null
    editLabelName.value = ''
    editingOriginalColor.value = ''

    taskSuccess.value = `✅ 已重命名为 "${newName}"，颜色保持不变`
    setTimeout(() => (taskSuccess.value = ''), 2000)
  } catch (error) {
    console.error('标签重命名失败:', error)
    await alertDialog({
      title: '错误',
      content: `修改失败: ${error.message}`,
      variant: 'error',
    })
  } finally {
    setTimeout(() => {
      editingOriginalColor.value = ''
    }, 500)
  }
}

const cancelLabelEdit = () => {
  editingLabel.value = null
  editLabelName.value = ''
  editingOriginalColor.value = ''
}
// ============ 模型切换（支持本地+云端） ============
const modelList = ref([])
const currentModel = ref('')

// 获取模型徽章样式
const getModelBadgeStyle = (modelName) => {
  const gradient = getModelColor(modelName)
  return { background: gradient.background }
}

// 加载模型列表 - 从本地API和Supabase数据库获取
const loadModelList = async () => {
  try {
    console.log('🔄 开始加载模型列表...')

    const models = []

    // 1. 从 training/status 获取本地模型
    try {
      const res = await fetch('/api/training/status')
      const data = await res.json()
      console.log('本地训练状态 API 返回:', data)

      if (data.local_models && Array.isArray(data.local_models)) {
        data.local_models.forEach(model => {
          models.push({
            id: `local_${model.name}`,
            name: model.name,
            path: model.path || model.name,
            source: '本地',
            type: getModelType(model.name),
            created_at: null,
            isCloud: false
          })
        })
      }

      // 设置当前使用的模型
      if (data.current_model) {
        currentModel.value = data.current_model
      }
    } catch (e) {
      console.warn('获取本地模型失败:', e)
    }

    // 2. 从 Supabase 数据库获取云端模型
    try {
      console.log('☁️ 从 Supabase 获取云端模型...')
      const { data: cloudModels, error } = await supabase
        .from('model_versions')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) {
        console.error('Supabase 查询失败:', error)
      } else if (cloudModels && cloudModels.length > 0) {
        console.log(`✅ 从数据库获取 ${cloudModels.length} 个云端模型:`, cloudModels)

        cloudModels.forEach(model => {
          // 避免重复添加（如果本地和云端有同名模型，优先显示云端版本）
          const existingIndex = models.findIndex(m => m.name === model.version_name)

          const cloudModel = {
            id: model.id,
            name: model.version_name,
            path: model.version_name, // 云端模型通过ID或名称引用
            source: '云端',
            type: getModelType(model.version_name),
            training_data_count: model.training_data_count,
            created_at: model.created_at,
            updated_at: model.updated_at,
            isCloud: true
          }

          if (existingIndex >= 0) {
            // 替换本地模型为云端模型（云端优先）
            models[existingIndex] = cloudModel
            console.log(`🔄 模型 ${model.version_name} 已存在本地版本，替换为云端版本`)
          } else {
            models.push(cloudModel)
          }
        })
      } else {
        console.log('ℹ️ 数据库中没有云端模型')
      }
    } catch (e) {
      console.error('获取云端模型失败:', e)
    }

    modelList.value = models
    console.log(`✅ 共加载了 ${modelList.value.length} 个模型（本地+云端）:`, modelList.value)

  } catch (e) {
    console.error('加载模型列表失败:', e)
    modelList.value = []
  }
}

// 切换模型
const switchModel = async (model) => {
  try {
    // 根据模型来源使用不同的API
    const endpoint = model.isCloud ? '/api/models/switch-cloud' : '/api/models/switch'

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: model.path,
        name: model.name,
        id: model.id,
        isCloud: model.isCloud
      }),
    })

    const data = await res.json()

    if (data.success) {
      currentModel.value = model.name
      taskSuccess.value = `✅ 已切换到${model.source}模型: ${model.name}`
      setTimeout(() => (taskSuccess.value = ''), 2000)
    } else {
      throw new Error(data.message || '切换失败')
    }
  } catch (e) {
    console.error('切换模型失败:', e)
    taskError.value = `❌ 切换失败: ${e.message}`
    setTimeout(() => (taskError.value = ''), 3000)
  }
}

const removeLabel = async (labelName) => {
  const usedCount = store.annotations.filter((ann) => ann.label === labelName).length

  if (usedCount > 0) {
    await alertDialog({
      title: '无法删除',
      content: `有 ${usedCount} 个标注正在使用该标签，请先删除相关标注`,
      variant: 'error',
    })
    return
  }

  const result = await confirmDialog({
    title: '确认删除',
    content: `确定删除标签 "${labelName}" 吗？`,
    variant: 'error',
  })

  if (result.confirmed) {
    try {
      const response = await fetch(`/api/labels/${encodeURIComponent(labelName)}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json()
        console.error('后端删除标签失败:', errorData)
      } else {
        console.log(`✅ 后端标签 ${labelName} 已删除`)
      }
    } catch (error) {
      console.error('删除标签请求失败:', error)
      const continueResult = await confirmDialog({
        title: '后端删除失败',
        content: '后端删除标签失败，是否仅在前端移除？刷新后可能会重新出现。',
        variant: 'warning',
      })
      if (!continueResult.confirmed) return
    }

    labelColorMap.delete(labelName)
    syncLabelsFromMap()

    if (currentLabel.value === labelName && labels.value.length > 0) {
      currentLabel.value = labels.value[0].name
      selectedColor.value = labelColorMap.get(currentLabel.value)
    }

    dragTick.value++
    taskSuccess.value = `✅ 标签 "${labelName}" 已删除`
    setTimeout(() => (taskSuccess.value = ''), 2000)
  }
}

const updateSelectedLabel = async () => {
  if (!selectedId.value) {
    await alertDialog({
      title: '提示',
      content: '请先选中一个标注',
      variant: 'info',
    })
    return
  }

  const annotation = store.annotations.find((ann) => ann.id === selectedId.value)
  if (!annotation) return

  const result = await promptDialog({
    title: '修改标签',
    content: '请输入新标签名称：',
    placeholder: '标签名称',
    defaultValue: annotation.label,
    variant: 'info',
  })

  if (!result.confirmed || !result.value?.trim()) return

  const trimmedLabel = result.value.trim()

  if (!labelColorMap.has(trimmedLabel)) {
    const newColor = generateColor(trimmedLabel)
    labelColorMap.set(trimmedLabel, newColor)
    syncLabelsFromMap()
  }

  annotation.label = trimmedLabel
  annotation.color = labelColorMap.get(trimmedLabel)
  dragTick.value++
  taskSuccess.value = `✅ 标签已修改为: ${trimmedLabel}`
  setTimeout(() => (taskSuccess.value = ''), 2000)
}

const updateSelectedAnnotationLabel = async () => {
  if (!selectedId.value) return

  const newLabelValue = editingAnnotationLabel.value.trim()
  if (!newLabelValue) return

  const annotation = store.annotations.find((ann) => ann.id === selectedId.value)
  if (!annotation) return

  if (!labelColorMap.has(newLabelValue)) {
    const color = generateColor(newLabelValue)
    labelColorMap.set(newLabelValue, color)
    await saveLabelToBackend(newLabelValue, color)
    syncLabelsFromMap()
  }

  annotation.label = newLabelValue
  annotation.color = labelColorMap.get(newLabelValue)

  currentLabel.value = newLabelValue
  selectedColor.value = labelColorMap.get(newLabelValue)

  dragTick.value++
  editingAnnotationLabel.value = ''
  taskSuccess.value = `✅ 标注标签已修改为: ${newLabelValue}`
  setTimeout(() => (taskSuccess.value = ''), 2000)
}

const updateSelectedAnnotationColor = async () => {
  if (!selectedId.value) {
    await alertDialog({ title: '提示', content: '请先选中一个标注', variant: 'info' })
    return
  }

  const annotation = store.annotations.find((ann) => ann.id === selectedId.value)
  if (!annotation) return

  const newColor = editingAnnotationColor.value

  labelColorMap.set(annotation.label, newColor)

  store.annotations.forEach((ann) => {
    if (ann.label === annotation.label) {
      ann.color = newColor
    }
  })

  try {
    await saveLabelToBackend(annotation.label, newColor)
  } catch (e) {
    console.error('保存颜色失败:', e)
  }

  syncLabelsFromMap()
  dragTick.value++

  taskSuccess.value = `✅ 标签 "${annotation.label}" 颜色已修改，影响 ${
    store.annotations.filter((a) => a.label === annotation.label).length
  } 个标注`
  setTimeout(() => (taskSuccess.value = ''), 2000)
}

const loadSavedLabels = async () => {
  try {
    const response = await fetch('/api/labels')
    const data = await response.json()

    if (data.labels && data.labels.length > 0) {
      // 清空并重新加载，避免重复
      labelColorMap.clear()

      for (const label of data.labels) {
        const name = label.name || label.label_name
        const color = label.color || label.label_color
        if (name) {
          labelColorMap.set(name, color || ensureLabelColor(name))
        }
      }

      syncLabelsFromMap()
      console.log(`📋 从后端加载 ${labels.value.length} 个标签`)
    }
  } catch (error) {
    console.error('加载后端标签失败:', error)
  }
}

const centerImage = () => {
  stageX.value = 0
  stageY.value = 0
  dragTick.value++
}

const loadImageFromSource = async (imageUrl) => {
  if (!imageUrl) return false

  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.src = imageUrl

  await new Promise((resolve, reject) => {
    img.onload = resolve
    img.onerror = () => reject(new Error('图片加载失败'))
    setTimeout(() => reject(new Error('图片加载超时')), 10000)
  })

  imageObj.value = img
  store.clearAnnotations()
  dragTick.value++
  return true
}

const loadPreAnnotations = (taskId) => {
  if (!taskId) return false

  const preData = localStorage.getItem(`pre_annotations_${taskId}`)
  if (preData) {
    try {
      const result = JSON.parse(preData)
      const anns = result.annotations || result

      if (anns && anns.length > 0) {
        anns.forEach((ann) => {
          if (!ann.color) {
            ann.color = labelColorMap.get(ann.label) || ensureLabelColor(ann.label)
          }
          if (!labelColorMap.has(ann.label)) {
            labelColorMap.set(ann.label, ann.color)
            saveLabelToBackend(ann.label, ann.color).catch(console.error)
          }
        })

        store.setAnnotations(anns)
        syncLabelsFromMap()
        dragTick.value++

        const firstAnn = anns[0]
        if (firstAnn) {
          currentLabel.value = firstAnn.label
          selectedColor.value = firstAnn.color || labelColorMap.get(firstAnn.label)
        }

        console.log(`✅ 已加载 ${anns.length} 个智能预标注框`)
        return true
      }
    } catch (e) {
      console.error('解析预标注数据失败:', e)
    }
  }
  return false
}

const loadProjectSettings = (projectId) => {
  const settings = localStorage.getItem(`project_keywords_${projectId}`)
  if (settings) {
    try {
      const data = JSON.parse(settings)
      console.log(
        '📋 项目标注模式:',
        data.use_keywords ? `关键词模式 (${data.keywords.join(', ')})` : '非关键词模式'
      )
      if (data.use_keywords && data.keywords.length > 0) {
        taskSuccess.value = `🎯 当前项目使用关键词: ${data.keywords.join(', ')}`
        setTimeout(() => (taskSuccess.value = ''), 3000)
      }
      return data
    } catch (e) {
      console.error('解析项目设置失败:', e)
    }
  }
  return null
}

const clearPreAnnotations = (taskId) => {
  if (taskId) {
    localStorage.removeItem(`pre_annotations_${taskId}`)
    console.log(`🧹 已清理任务 ${taskId} 的预标注缓存`)
  }
}

const taskList = ref([])
const currentTaskIndex = ref(0)
const totalTasks = ref(0)

const canGoPrev = computed(() => currentTaskIndex.value > 0)
const canGoNext = computed(() => currentTaskIndex.value < totalTasks.value - 1)

const taskNavigatorText = computed(() => {
  if (totalTasks.value === 0) return '无任务'
  return `${currentTaskIndex.value + 1} / ${totalTasks.value}`
})

onMounted(async () => {
  console.log('🚀 组件挂载完成')

  const defaultLabels = [
    { name: 'person', color: '#ff0000' },
    { name: 'car', color: '#0000ff' },
    { name: 'dog', color: '#00ff00' },
  ]
  defaultLabels.forEach((label) => ensureLabelColor(label.name, label.color))
  await loadSavedLabels()

    await loadModelList()

  if (routeProjectId.value && routeTaskId.value) {
    console.log(`📥 加载项目任务: ${routeProjectId.value}, 任务ID: ${routeTaskId.value}`)

    const hasTaskList = await loadTaskListFromStorage()

    if (!hasTaskList) {
      taskList.value = [
        {
          task_id: routeTaskId.value,
          file_id: '',
          filename: '',
          image_url: '',
          status: 'labeling',
          project_id: routeProjectId.value,
          use_keywords: route.query.sourceMode === 'keyword',
          keywords: [],
        },
      ]
      totalTasks.value = 1
      currentTaskIndex.value = 0
    }

    const loaded = await fetchProjectTask(routeProjectId.value, routeTaskId.value)

    if (!loaded) {
      loadTestImage()
    } else {
      loadProjectSettings(routeProjectId.value)

      const hasPreAnnotations = loadPreAnnotations(routeTaskId.value)
      updateCurrentTaskIndex(routeTaskId.value)

      if (totalTasks.value > 1) {
        taskSuccess.value = `✅ 已进入批量标注模式，${taskNavigatorText.value}${
          hasPreAnnotations ? '，已加载AI预标注' : ''
        }`
        setTimeout(() => (taskSuccess.value = ''), 3000)
      } else if (routeBatchSize.value > 0) {
        taskSuccess.value = `✅ 已进入批量标注模式，共 ${routeBatchSize.value} 张图片，当前: ${
          routeTaskId.value
        }${hasPreAnnotations ? '，已加载AI预标注' : ''}`
        setTimeout(() => (taskSuccess.value = ''), 3000)
      } else if (hasPreAnnotations) {
        taskSuccess.value = `✅ 已加载任务 ${routeTaskId.value}，智能预标注已应用`
        setTimeout(() => (taskSuccess.value = ''), 2500)
      }
    }
  } else if (typeof route.query.sourceImage === 'string' && route.query.sourceImage) {
    try {
      await loadImageFromSource(route.query.sourceImage)
      taskSuccess.value = `✅ 已加载测试图片：${route.query.sourceName || '来自项目选中图片'}`
      setTimeout(() => {
        taskSuccess.value = ''
      }, 2500)
    } catch (error) {
      console.error('❌ 项目测试图片加载失败:', error)
      taskError.value = '项目图片加载失败，已切换到默认测试图片'
      loadTestImage()
    }
  } else {
    const urlParams = new URLSearchParams(window.location.search)
    let taskId = urlParams.get('task')

    if (!taskId) {
      taskId = localStorage.getItem('lastTaskId')
      if (taskId) {
        window.history.replaceState({}, '', `?task=${taskId}`)
      }
    }

    if (taskId) {
      console.log('🔍 尝试恢复任务:', taskId)

      await loadTaskListFromStorage()
      const restored = await restoreTask(taskId)

      if (restored && store.taskInfo?.imageUrl) {
        console.log('✅ 任务恢复成功')

        loadPreAnnotations(taskId)
        updateCurrentTaskIndex(taskId)

        syncLabelsFromMap()
        dragTick.value++
      } else {
        console.warn('⚠️ 任务恢复失败，加载测试图片')
        loadTestImage()
        localStorage.removeItem('lastTaskId')
      }
    } else {
      loadTestImage()
    }
  }

  let resizeObserver = null
  if (canvasContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      dragTick.value++
    })
    resizeObserver.observe(canvasContainer.value)
  }

  const globalMouseUpHandler = (e) => {
    if (dialogLock.value) return
    if (e.target?.closest('.dialog-container')) return
    if (isDrawing.value) {
      const mouseUpHandler = handleMouseUp(currentLabel.value)
      mouseUpHandler({ target: stage.value?.getNode() })
    }
  }

  window.addEventListener('mouseup', globalMouseUpHandler)
  window.addEventListener('keydown', handleKeydown, true)

  if (canvasContainer.value) {
    canvasContainer.value.addEventListener('wheel', handleWheel, { passive: false })
  }

  const handleKeyDown = (e) => {
    if (e.code === 'Space' && !e.repeat) {
      e.preventDefault()
      setSpacePressed(true)
      const stageNode = stage.value?.getNode()
      if (stageNode && !isPanning.value) {
        stageNode.container().style.cursor = 'grab'
      }
    }
  }

  const handleKeyUp = (e) => {
    if (e.code === 'Space') {
      setSpacePressed(false)
      const stageNode = stage.value?.getNode()
      if (stageNode && !isPanning.value) {
        stageNode.container().style.cursor = 'default'
      }
    }
  }

  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)

  onUnmounted(() => {
    console.log('🧹 组件卸载，清理事件监听')
    window.removeEventListener('keydown', handleKeydown)
    window.removeEventListener('mouseup', globalMouseUpHandler)
    window.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('keyup', handleKeyUp)

    if (canvasContainer.value) {
      canvasContainer.value.removeEventListener('wheel', handleWheel)
    }
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
  })
})

watch(
  imageObj,
  async (newImg) => {
    if (newImg && canvasContainer.value) {
      await nextTick()
      const container = canvasContainer.value
      console.log('🖼️ 图片切换:', {
        imgWidth: newImg.width,
        imgHeight: newImg.height,
        containerWidth: container.clientWidth,
        containerHeight: container.clientHeight,
        computedSize: containerSize.value,
      })
      dragTick.value++
    }
  },
  { immediate: false }
)
</script>

<style scoped>
@import './AnnotateView.css';
</style>
