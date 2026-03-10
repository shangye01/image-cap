<template>
  <div class="annotation-workspace">
    <aside class="toolbar-panel">
   
<section class="tool-section training-section">
  <div class="section-header">
    <h3 class="section-title">🚀 模型训练</h3>
  </div>
  <div class="section-content">
    <div v-if="trainingStatus.dataset_ready" class="dataset-status ready">
      ✅ 数据集就绪: {{ trainingStatus.dataset_stats?.train || 0 }} 张训练图
    </div>
    <div v-else class="dataset-status error">
      ⚠️ {{ trainingStatus.dataset_message || '检查数据集...' }}
    </div>
    
    <div v-if="trainingStatus.cuda_available" class="gpu-info">
      🎮 GPU: {{ trainingStatus.cuda_device }}
    </div>
    <div v-else class="gpu-info warning">
      ⚠️ 使用CPU训练（较慢）
    </div>

    <div class="form-group">
      <label>训练轮数</label>
      <input type="number" v-model="trainingConfig.epochs" min="50" max="300" class="input-field">
    </div>

    <div class="form-group">
      <label>模型大小</label>
      <select v-model="trainingConfig.model_size" class="input-field">
        <option value="auto">自动选择</option>
        <option value="n">Nano (快)</option>
        <option value="s">Small</option>
        <option value="m">Medium</option>
        <option value="l">Large (准)</option>
        <option value="x">XLarge (最准)</option>
      </select>
    </div>

    <button 
      @click="startTraining" 
      :disabled="!trainingStatus.dataset_ready || trainingLoading"
      class="btn btn-primary"
    >
      {{ trainingLoading ? '训练中...' : '🚀 开始训练' }}
    </button>

    <div v-if="trainingMessage" :class="['message', trainingMessage.type]">
      {{ trainingMessage.text }}
    </div>

    <div v-if="trainingStatus.local_models?.length" class="model-list">
      <h4>可用模型</h4>
      <div 
        v-for="model in trainingStatus.local_models" 
        :key="model.name"
        :class="['model-item', { active: model.name === trainingStatus.current_model }]"
        @click="switchModel(model)"
      >
        <span class="model-name">{{ model.name }}</span>
        <span v-if="model.name === trainingStatus.current_model" class="current-badge">当前</span>
      </div>
    </div>
  </div>
</section>
      <section class="tool-section task-section">
        <div class="section-header">
          <h3 class="section-title">🎯 任务管理</h3>
        </div>
        <div class="section-content">
          <div v-if="store.currentTaskId" class="task-info">
            <div class="task-item">
              <span class="task-label">任务ID:</span>
              <span class="task-value">{{ store.currentTaskId }}</span>
            </div>
            <div class="task-item">
              <span class="task-label">项目:</span>
              <span class="task-value">{{ store.currentProjectId || '未指定' }}</span>
            </div>
            <div class="task-item">
              <span class="task-label">状态:</span>
              <span class="task-value" style="color: #52c41a;">标注中</span>
            </div>
          </div>
          <div v-else class="task-empty">
            <div class="empty-icon">📋</div>
            <p>暂无任务</p>
          </div>
          <div v-if="taskError" class="message error">⚠️ {{ taskError }}</div>
          <div v-if="taskSuccess" class="message success">✅ {{ taskSuccess }}</div>
          
          <button @click="loadNextTask()" class="btn btn-primary" :disabled="taskLoading || submitLoading">
            {{ taskLoading ? '⏳ 获取中...' : '🎯 获取新任务' }}
          </button>
          
          <button @click="submitAnnotations()" class="btn btn-success" :disabled="!store.currentTaskId || submitLoading || store.annotations.length === 0">
            {{ submitLoading ? '⏳ 提交中...' : '✅ 提交标注' }}
          </button>
          
          <button @click="saveDraftHandler()" class="btn btn-secondary" :disabled="!store.currentTaskId || store.annotations.length === 0">
            💾 保存草稿
          </button>
          
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
          <input type="file" ref="fileInput" @change="handleFileUpload" accept="image/*" style="display: none">
          <button @click="$refs.fileInput.click()" class="btn btn-secondary">上传本地图片</button>
          <div class="divider"></div>
          <button @click="runSmartAnnotation()" class="btn btn-success" :disabled="!imageObj || predicting">
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
    
    <div class="pan-controls" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e8e8e8;">
      <div class="pan-info" style="font-size: 12px; color: #666; margin-bottom: 8px;">
        📍 位置: X: {{ Math.round(stageX) }}, Y: {{ Math.round(stageY) }}
      </div>
      <div class="pan-buttons" style="display: flex; gap: 8px;">
        <button 
          @click="resetPan()" 
          class="btn btn-secondary btn-small" 
          style="flex: 1;"
          title="重置位置"
        >
          🎯 重置位置
        </button>
        <button 
          @click="centerImage()" 
          class="btn btn-primary btn-small" 
          style="flex: 1;"
          title="居中图片"
        >
          ⭕ 居中
        </button>
      </div>
      <div class="pan-hint" style="font-size: 11px; color: #999; margin-top: 8px;">
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
          <div class="section-header" @click="collapsedSections.selected = !collapsedSections.selected">
            <h3 class="section-title">🎯 选中标注</h3>
            <span class="collapse-btn">▼</span>
          </div>
          <div class="section-content">
            <div class="selected-annotation-info">
              <div class="info-row">
                <span class="info-label">标签名称：</span>
                <span class="info-value" :style="{ color: selectedAnnotation.color || labelColorMap.get(selectedAnnotation.label) }">
                  <span class="color-dot" :style="{ backgroundColor: selectedAnnotation.color || labelColorMap.get(selectedAnnotation.label) }"></span>
                  <strong>{{ selectedAnnotation.label }}</strong>
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">位置坐标：</span>
                <span class="info-value">X: {{ Math.round(selectedAnnotation.x) }}, Y: {{ Math.round(selectedAnnotation.y) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">尺寸大小：</span>
                <span class="info-value">{{ Math.round(selectedAnnotation.width) }} × {{ Math.round(selectedAnnotation.height) }} px</span>
              </div>
              <div class="info-row" v-if="selectedAnnotation.confidence">
                <span class="info-label">置信度：</span>
                <span class="info-value">{{ (selectedAnnotation.confidence * 100).toFixed(1) }}%</span>
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
              <button 
                @click="updateSelectedAnnotationColor" 
                class="btn btn-small btn-success"
              >
                改色
              </button>
              <button 
                @click="updateSelectedAnnotationLabel" 
                class="btn btn-small btn-primary"
              >
                修改
              </button>
            </div>
            <div class="editor-row">
              <input 
                type="color" 
                v-model="editingAnnotationColor" 
                class="color-picker-full"
              />
            </div>
          </div>
          
          <div v-else class="add-label-section">
            <div class="current-label-display">
              <span class="color-dot" :style="{ backgroundColor: selectedColor }"></span>
              <span class="current-label-text">{{ currentLabel }}</span>
            </div>
            <div class="input-group">
              <input v-model="newLabel" placeholder="新标签名称" class="input-field" @keyup.enter="addLabel">
              <input type="color" v-model="selectedColor" class="color-picker">
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
                  <span class="color-dot" :style="{ 
          backgroundColor: labelColorMap.get(label.name) || label.color 
        }"></span>
                  {{ label.name }}
                  <span v-if="annotations.filter(ann => ann.label === label.name).length > 0" class="label-count">
                    {{ annotations.filter(ann => ann.label === label.name).length }}
                  </span>
                </div>
                <div class="label-actions">
                  <button class="btn-icon" @click.stop="startEditLabel(label)" title="编辑标签">✏️</button>
                  <button class="btn-icon btn-danger" @click.stop="removeLabel(label.name)" title="删除标签">🗑️</button>
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
                  <button class="btn-icon btn-success" @click="saveLabelEdit(label.name)" title="保存">✅</button>
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
          :disabled="!selectedId || dialogLock.value"
        >
          🗑️ 删除选中标注
        </button>
        <div class="divider"></div>
      </section>

      <section class="tool-section export-section">
        <button @click.stop="clearAll()" class="btn btn-danger" :disabled="annotations.length === 0">
          清除所有标注
        </button>
        <button @click.stop="exportAnnotations()" class="btn btn-success" :disabled="annotations.length === 0">
          💾 导出JSON
        </button>
        <button @click.stop="exportForYOLO" class="btn btn-success" :disabled="annotations.length === 0">
          📦 导出YOLO
        </button>
      </section>
    </aside>

    <main class="canvas-container" ref="canvasContainer">
      <div v-if="imageObj" class="canvas-wrapper"   
      :class="{ panning: isSpacePressed || isPanning }">
        <v-stage ref="stageRef" 
         :config="scaledStageConfig" 
         @mousedown="handleMouseDown" 
         @mousemove="handleMouseMove" 
         @mouseup="handleMouseUp(currentLabel)" 
         @click="handleStageClick">
          <v-layer ref="layer">
           <v-image :config="scaledImageConfig" />
            <v-rect
           v-if="isDrawing && drawingRect"
           :config="getDrawingRectConfig()"  
          />
            <v-rect 
              v-for="ann in annotations" 
              :key="ann.id" 
              :config="getRectConfig(ann)" 
              @click="(e) => selectAnnotation(e, ann.id)"  
              @dragend="(e) => handleRectDragEnd(e, ann.id)" 
              @dragmove="() => handleRectDragMove(ann.id)" 
            />
            <v-text v-for="ann in annotations" :key="`label-${ann.id}-${dragTick}`" :config="getTextConfig(ann)" />
            <v-transformer ref="transformer" :config="transformerConfig" @transformstart="handleTransformStart" @transformend="(e) => handleTransformEnd(e, selectedId)" />
          </v-layer>
        </v-stage>
      </div>
      <div v-else class="empty-state">
        <div class="empty-icon">📷</div>
        <p>请加载图片开始标注</p>
        <button @click="loadTestImage()" class="btn btn-primary" style="margin-top: 16px;">加载测试图片</button>
      </div>
    </main>
  </div>
</template>

<script setup>
// ✅ 1. 引入 shallowRef (修复图片显示BUG的关键)
import { ref, computed, reactive, onMounted, onUnmounted, watch, toRef, nextTick, shallowRef } from 'vue'
import { useAnnotationStore } from '@/stores/annotation'
import { useColorManager } from '@/composables/useColorManager'
import { useCanvasEvents } from '@/composables/useCanvasEvents'
import { useTaskFlow } from '@/composables/useTaskFlow'
import { useAnnotationApi } from '@/composables/useAnnotationApi'
import { confirmDialog, promptDialog, alertDialog } from '@/composables/useDialog'
import { supabase } from '@/supabase'
import { useAutoSave } from '@/supabase'
import { apiUrl, resolveAssetUrl } from '@/config/api'
const store = useAnnotationStore()

// ========== 响应式状态定义 ==========
// ✅ 2. 修改 imageObj 为 shallowRef
// 普通 ref 会深度代理 Image 对象，导致 Konva 无法识别，从而出现图片不显示的问题
const imageObj = shallowRef(null)
const fileInput = ref(null)
const transformer = ref(null)
const layer = ref(null)
const canvasContainer = ref(null)
const stageRef = ref(null)  
const newLabel = ref('')
const selectedColor = ref('#ff0000')
const currentLabel = ref('object')
const collapsedSections = reactive({
  image: false,
  label: false,
  stats: false,
  selected: false,
  zoom: false 
})

const editingLabel = ref(null)
const editLabelName = ref('')
const editingOriginalColor = ref('')
const editingAnnotationLabel = ref('')
const editingAnnotationColor = ref('#ff0000')
const dialogLock = ref(false)

// ========== 缩放相关状态 ==========
const zoomScale = ref(1)
const MIN_ZOOM = 0.1
const MAX_ZOOM = 5
const ZOOM_STEP = 0.1

// ========== 容器尺寸计算 ==========
const baseContainerSize = computed(() => {
  if (!canvasContainer.value) {
    return { width: 800, height: 600, scale: 1 }
  }
  
  // 使用 naturalWidth/naturalHeight 获取原始尺寸
  const imgWidth = imageObj.value?.naturalWidth || imageObj.value?.width || 800
  const imgHeight = imageObj.value?.naturalHeight || imageObj.value?.height || 600
  
  const container = canvasContainer.value
  const padding = 40
  const maxWidth = Math.max(100, container.clientWidth - padding)
  const maxHeight = Math.max(100, container.clientHeight - padding)
  
  const scale = Math.min(
    maxWidth / imgWidth,
    maxHeight / imgHeight,
    1
  )
  
  return {
    width: imgWidth * scale,
    height: imgHeight * scale,
    scale: scale
  }
})

const containerSize = computed(() => {
  const base = baseContainerSize.value
  return {
    width: base.width * zoomScale.value,
    height: base.height * zoomScale.value,
    scale: base.scale * zoomScale.value
  }
})

// ========== Stage 配置 ==========
const scaledStageConfig = computed(() => {
  const base = baseContainerSize.value
  
  const config = {
    width: Math.max(1, base.width * zoomScale.value),
    height: Math.max(1, base.height * zoomScale.value),
    scaleX: 1,
    scaleY: 1,
    containerStyle: {
      backgroundColor: '#e8e8e8'
    }
  }
  
  return config
})

// ========== 计算属性 ==========
watch(currentLabel, (label) => {
  selectedColor.value = labelColorMap.get(label) || '#ff0000'
})

const drawingColor = computed(() => {
  return labelColorMap.get(currentLabel.value) || '#ff0000'
})

const annotations = computed(() => store.annotations || [])
const selectedId = computed(() => store.selectedId)

const selectedAnnotation = computed(() => {
  return annotations.value.find(a => a.id === selectedId.value)
})

// ========== 缩放控制函数 ==========
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
  const oldScale = zoomScale.value
  const baseScale = baseContainerSize.value.scale
  zoomScale.value = 1 / baseScale
  
  const base = baseContainerSize.value
  const centerX = base.width / 2
  const centerY = base.height / 2
  
  stageX.value = centerX - (centerX - stageX.value) * (zoomScale.value / oldScale)
  stageY.value = centerY - (centerY - stageY.value) * (zoomScale.value / oldScale)
  
  updateZoom()
}

const updateZoom = () => {
  dragTick.value++
  
  // ✅ 修复：安全获取 transformer 和 stage
  nextTick(() => {
    if (transformer.value) {
      const tr = transformer.value.getNode?.() || transformer.value
      if (tr && tr.forceUpdate) {
        tr.forceUpdate()
      }
    }
    
    // 强制刷新 stage
    const stageNode = stageRef.value?.getStage?.() || stageRef.value?.getNode?.()
    if (stageNode && stageNode.batchDraw) {
      stageNode.batchDraw()
    }
  })
}

const handleWheel = (e) => {
  if (!imageObj.value) return
  if (!e.ctrlKey && !e.metaKey) return
  
  e.preventDefault()
  
  // ✅ 修复：安全获取 stage 节点
  const stageNode = stageRef.value?.getStage?.() || stageRef.value?.getNode?.()
  if (!stageNode) {
    console.warn('⚠️ handleWheel: 无法获取 stage 节点')
    return
  }
  
  const oldScale = zoomScale.value
  const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
  const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomScale.value + delta))
  
  if (newScale !== oldScale) {
    const pointer = stageNode.getPointerPosition()
    if (!pointer) return
    
    const base = baseContainerSize.value
    
    const mouseX = (pointer.x - stageX.value) / oldScale
    const mouseY = (pointer.y - stageY.value) / oldScale
    
    zoomScale.value = newScale
    
    stageX.value = pointer.x - mouseX * newScale
    stageY.value = pointer.y - mouseY * newScale
    
    updateZoom()
  }
}

// ========== Composables ==========
const { 
  labelColorMap, 
  COLOR_POOL, 
  generateColor, 
  ensureLabelColor, 
  syncLabelsFromMap,
  labels
} = useColorManager([
  { id: 1, name: 'person', color: '#ff0000' },
  { id: 2, name: 'car', color: '#0000ff' },
  { id: 3, name: 'dog', color: '#00ff00' }
])

const dragTick = ref(0)

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
  restoreTask
} = useTaskFlow(store, imageObj, labelColorMap, dragTick)

// ✅ 监听 imageObj 变化
// ========== 修复后的 imageObj 监听器 ==========
watch(imageObj, async (newImg, oldImg) => {
  console.log('👁️ [watch imageObj] 变化触发')
  console.log(`   新值: ${newImg ? '存在' : 'null'}`)
  console.log(`   旧值: ${oldImg ? '存在' : 'null'}`)
  
  if (!newImg) {
    console.log('   🚫 新图片为空，跳过')
    return
  }
  
  // 如果图片未完全加载，等待加载完成
  if (!newImg.complete || newImg.naturalWidth === 0) {
    console.log('⏳ [watch imageObj] 等待图片加载完成...')
    await new Promise((resolve) => {
      const onLoad = () => {
        newImg.removeEventListener('load', onLoad)
        newImg.removeEventListener('error', onError)
        console.log('✅ [watch imageObj] 图片 onload 触发')
        resolve()
      }
      const onError = () => {
        console.error('❌ [watch imageObj] 图片加载失败')
        newImg.removeEventListener('load', onLoad)
        newImg.removeEventListener('error', onError)
        resolve()
      }
      newImg.addEventListener('load', onLoad)
      newImg.addEventListener('error', onError)
    })
  }
  
  console.log(`✅ [watch imageObj] 图片就绪: ${newImg.naturalWidth} x ${newImg.naturalHeight}`)
  
  // 强制刷新
  await nextTick()
  dragTick.value++
  
  // 延迟再次刷新确保渲染
  setTimeout(() => {
    dragTick.value++
    if (stageRef.value) {
      const stageNode = stageRef.value.getNode()
      if (stageNode && typeof stageNode.batchDraw === 'function') {
        stageNode.batchDraw()
        console.log('🔄 [watch imageObj] Stage batchDraw 执行')
      }
    }
  }, 100)
  
}, { immediate: true, flush: 'post' })

const {
  isDrawing,
  drawingRect,
  isTransforming,
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
  setSpacePressed
} = useCanvasEvents(baseContainerSize, selectedColor, labelColorMap, store, transformer, layer, annotations, currentLabel)

const {
  predicting,
  runSmartAnnotation
} = useAnnotationApi(
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

const { save: autoSave } = useAutoSave(
  toRef(store, 'currentTaskId'),
  toRef(store, 'annotations')
)

watch(() => store.annotations, (newVal) => {
  if (store.currentTaskId && newVal.length > 0) {
    autoSave()
  }
}, { deep: true })

// ========== 配置函数 ==========
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
    listening: false
  }
}

const trainingStatus = ref({
  dataset_ready: false,
  dataset_stats: {},
  local_models: [],
  current_model: '',
  cuda_available: false
})
const trainingConfig = ref({
  epochs: 100,
  model_size: 'auto'
})
const trainingLoading = ref(false)
const trainingMessage = ref(null)

const checkTrainingStatus = async () => {
  try {
    const res = await fetch(apiUrl('/api/training/status'))
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
      augmentation: true
    })
    
   const res = await fetch(apiUrl(`/api/training/start?${params}`), {
      method: 'POST'
    })
    const data = await res.json()
    
    if (data.success) {
      trainingMessage.value = {
        type: 'success',
        text: `训练已启动！模型: ${data.config.model_size}, 轮数: ${data.config.epochs}`
      }
      setInterval(checkTrainingStatus, 10000)
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    trainingMessage.value = {
      type: 'error',
      text: '启动失败: ' + e.message
    }
  } finally {
    trainingLoading.value = false
  }
}

const switchModel = async (model) => {
  try {
   const res = await fetch(apiUrl('/api/models/switch'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: model.path, name: model.name })
    })
    const data = await res.json()
    if (data.success) {
      alert('模型已切换: ' + model.name)
      checkTrainingStatus()
    }
  } catch (e) {
    alert('切换失败: ' + e.message)
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
    shadowOpacity: 0.3
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
    opacity: isSelected ? 1 : (ann.confidence ? 0.6 + ann.confidence * 0.4 : 1),
    shadowEnabled: isSelected,
    shadowColor: 'rgba(0, 0, 0, 0.3)',
    shadowBlur: 4,
    shadowOffsetY: 2
  }
}

// ========== 修复后的 scaledImageConfig ==========
const scaledImageConfig = computed(() => {
  console.log('🔧 [scaledImageConfig] 重新计算...')
  
  if (!imageObj.value) {
    console.log('   ⚠️ imageObj 为空，返回空配置')
    return { image: null, width: 0, height: 0, x: 0, y: 0 }
  }
  
  // 使用 naturalWidth/naturalHeight 获取原始尺寸
  const imgWidth = imageObj.value.naturalWidth || imageObj.value.width || 0
  const imgHeight = imageObj.value.naturalHeight || imageObj.value.height || 0
  
  console.log(`   图片原始尺寸: ${imgWidth} x ${imgHeight}`)
  
  if (imgWidth === 0 || imgHeight === 0) {
    console.warn('   ⚠️ 图片尺寸为0，可能尚未加载完成')
    return { image: null, width: 0, height: 0, x: 0, y: 0 }
  }
  
  const base = baseContainerSize.value
  
  const config = {
    image: imageObj.value,
    x: stageX.value * zoomScale.value,
    y: stageY.value * zoomScale.value,
    width: imgWidth * base.scale * zoomScale.value,
    height: imgHeight * base.scale * zoomScale.value,
    name: 'background-image'
  }
  
  console.log(`   最终配置: ${config.width.toFixed(1)} x ${config.height.toFixed(1)}`)
  return config
})

const transformerConfig = computed(() => {
  if (!selectedId.value) {
    return { visible: false }
  }

  const ann = annotations.value.find(a => a.id === selectedId.value)
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
    }
  }
})

// ========== 业务函数 ==========
const exportForYOLO = async () => {
  if (annotations.value.length === 0) {
    await alertDialog({
      title: '提示',
      content: '没有标注数据',
      variant: 'info'
    })
    return
  }
  
  const imgWidth = imageObj.value.width
  const imgHeight = imageObj.value.height
  
  const yoloData = annotations.value.map(ann => {
    const classId = labels.value.findIndex(l => l.name === ann.label)
    const centerX = (ann.x + ann.width / 2) / imgWidth
    const centerY = (ann.y + ann.height / 2) / imgHeight
    const normWidth = ann.width / imgWidth
    const normHeight = ann.height / imgHeight
    
    return `${classId} ${centerX.toFixed(6)} ${centerY.toFixed(6)} ${normWidth.toFixed(6)} ${normHeight.toFixed(6)}`
  }).join('\n')

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

// ========== 文件上传处理（图片加载部分修复） ==========
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  console.log('📤 [handleFileUpload] 开始上传:', file.name, file.size)
  taskLoading.value = true
  taskError.value = ''
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(apiUrl('/api/predict'), {
      method: 'POST',
      body: formData
    })
    
    const data = await response.json()
    console.log('📥 [handleFileUpload] 后端响应:', data)
    
    if (!response.ok) {
      throw new Error(data.detail || '上传失败')
    }
    
    // 保存任务信息
    localStorage.setItem('lastTaskId', data.task_id)
    window.history.replaceState({}, '', `/app/annotate?task=${data.task_id}`)
    
    store.clearAnnotations()
    store.setCurrentTask({ 
      id: data.task_id, 
      imageUrl: resolveAssetUrl(data.image_url),
      imageStoragePath: data.image_storage_path
    })
    
    // 创建图片对象并等待加载
    const img = new Image()
    img.crossOrigin = 'anonymous'
    
    // 关键修复：使用 Promise 等待图片加载
    await new Promise((resolve, reject) => {
      img.onload = () => {
        console.log('✅ [handleFileUpload] 图片加载成功:', img.naturalWidth, 'x', img.naturalHeight)
        resolve()
      }
      img.onerror = () => reject(new Error('图片加载失败'))
      
      // 添加时间戳防止缓存
      const imageSrc = resolveAssetUrl(data.image_url)
      const separator = imageSrc.includes('?') ? '&' : '?'
      img.src = `${imageSrc}${separator}t=${Date.now()}`
      console.log('🔥 [handleFileUpload] 图片 src:', img.src)
    })
    
    // 等待解码
    if (img.decode) await img.decode()
    
    // 赋值给 shallowRef
    imageObj.value = img
    console.log('✅ [handleFileUpload] imageObj 已设置')
    
    await nextTick()
    dragTick.value++
    
    // 处理标注数据
    if (data.annotations && data.annotations.length > 0) {
      console.log(`📝 [handleFileUpload] 处理 ${data.annotations.length} 个标注`)
      
      // 处理标签颜色
      const newLabelsToSave = []
      data.annotations.forEach(ann => {
        if (!ann.color) {
          ann.color = labelColorMap.get(ann.label) || ensureLabelColor(ann.label)
        }
        
        if (!labelColorMap.has(ann.label)) {
          labelColorMap.set(ann.label, ann.color)
          newLabelsToSave.push({ name: ann.label, color: ann.color })
        }
      })
      
      // 保存新标签到后端
      for (const label of newLabelsToSave) {
        try {
          await saveLabelToBackend(label.name, label.color)
        } catch (e) {
          console.error(`❌ 保存标签 ${label.name} 失败:`, e)
        }
      }
      
      // 设置当前标签为第一个标注的标签
      if (data.annotations.length > 0) {
        currentLabel.value = data.annotations[0].label
        selectedColor.value = labelColorMap.get(currentLabel.value) || '#ff0000'
      }
      
      syncLabelsFromMap()
      store.setAnnotations(data.annotations)
    }
    
    // 强制刷新 Stage
    setTimeout(() => {
      if (stageRef.value) {
        const stageNode = stageRef.value.getNode()
        if (stageNode) {
          stageNode.batchDraw()
          console.log('🔄 [handleFileUpload] Stage 已刷新')
        }
      }
    }, 100)
    
    const stats = data.stats || {}
    taskSuccess.value = `✅ 上传成功，检测到 ${stats.final_count || data.annotations?.length || 0} 个目标`
    setTimeout(() => taskSuccess.value = '', 3000)
    
  } catch (error) {
    console.error('❌ [handleFileUpload] 错误:', error)
    taskError.value = `❌ 上传失败: ${error.message}`
  } finally {
    taskLoading.value = false
    event.target.value = ''
  }
}
const saveLabelToBackend = async (name, color) => {
  try {
   const response = await fetch(apiUrl('/api/labels'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        name: name, 
        color: color, 
        category: null 
      })
    })
    
    if (response.ok) {
      return
    }
    
    const errorData = await response.json()
    if (response.status === 409 || errorData.detail?.includes('已存在')) {
      await fetch(apiUrl(`/api/labels/${encodeURIComponent(name)}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color: color })
      })
    }
  } catch (error) {
    console.error('保存标签失败:', error)
  }
}

const addLabel = async () => {
  if (!newLabel.value.trim()) {
    await alertDialog({
      title: '提示',
      content: '请输入标签名称',
      variant: 'info'
    })
    return
  }
  
  const labelName = newLabel.value.trim()
  const exists = labels.value.some(l => l.name === labelName)
  if (exists) {
    await alertDialog({
      title: '提示',
      content: '标签已存在',
      variant: 'info'
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
  const result = await confirmDialog({
    title: '确认清除',
    content: '确定清除所有标注吗？此操作不可撤销。',
    variant: 'error'
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
      variant: 'info'
    })
    return
  }
  
  const data = { 
    image: { width: imageObj.value.width, height: imageObj.value.height }, 
    annotations: annotations.value 
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
  if (!selectedId.value || dialogLock.value) {
    return
  }
  
  const annotation = annotations.value.find(a => a.id === selectedId.value)
  if (!annotation) return

  dialogLock.value = true
  
  try {
    const result = await confirmDialog({
      title: '删除标注',
      content: `确定要删除标注 "${annotation.label}" 吗？此操作无法撤销。`,
      variant: 'error'
    })
    
    if (result.confirmed) {
      deleteAnnotation(selectedId.value)
    } 
  } catch (error) {
    console.error('🔥 [Delete] 删除过程出错:', error)
  } finally {
    setTimeout(() => {
      dialogLock.value = false
    }, 300)
  }
}

const handleKeydown = async (e) => {
  if (dialogLock.value) {
    return
  }

  const activeElement = document.activeElement
  const isInInput = activeElement && ['INPUT', 'TEXTAREA'].includes(activeElement.tagName)
  if (isInInput) return

  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId.value) {
    e.preventDefault()
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
  
  if (!color) {
    color = labelColorMap.get(label.name)
  }
  
  if (!color) {
    color = '#ff0000'
  }
  
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
  
  if (!color) {
    color = labelColorMap.get(oldName)
  }
  
  if (!color) {
    const annotation = store.annotations.find(ann => ann.label === oldName)
    color = annotation?.color
  }
  
  if (!color) {
    color = '#ff0000'
  }
  

  try {
    const createRes = await fetch(apiUrl('/api/labels'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        name: newName, 
        color: color,
        category: null 
      })
    })
    
    if (!createRes.ok) {
      const errorData = await createRes.json()
      if (errorData.detail?.includes('已存在')) {
       await fetch(apiUrl(`/api/labels/${encodeURIComponent(newName)}`), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ color: color })
        })
      } else {
        throw new Error(errorData.detail || '创建新标签失败')
      }
    }
    
    try {
      await fetch(apiUrl(`/api/labels/${encodeURIComponent(oldName)}`), {
        method: 'DELETE'
      })
    } catch (e) {
      console.log('删除旧标签失败（可能后端没有该记录）:', e)
    }
    
    labelColorMap.delete(oldName)
    labelColorMap.set(newName, color)
    
    const oldLabelIndex = labels.value.findIndex(l => l.name === oldName)
    if (oldLabelIndex !== -1) {
      labels.value[oldLabelIndex] = {
        id: labels.value[oldLabelIndex].id,
        name: newName,
        color: color
      }
    } else {
      labels.value.push({
        id: `label_${Date.now()}`,
        name: newName,
        color: color
      })
    }
    
    let updatedCount = 0
    store.annotations.forEach(ann => {
      if (ann.label === oldName) {
        ann.label = newName
        ann.color = color
        updatedCount++
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
    
    taskSuccess.value = `✅ 已重命名为 "${newName}"`
    setTimeout(() => taskSuccess.value = '', 2000)
    
  } catch (error) {
    console.error('标签重命名失败:', error)
    await alertDialog({
      title: '错误',
      content: `修改失败: ${error.message}`,
      variant: 'error'
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

const removeLabel = async (labelName) => {
  const usedCount = store.annotations.filter(ann => ann.label === labelName).length
  
  if (usedCount > 0) {
    await alertDialog({
      title: '无法删除',
      content: `有 ${usedCount} 个标注正在使用该标签，请先删除相关标注`,
      variant: 'error'
    })
    return
  }
  
  const result = await confirmDialog({
    title: '确认删除',
    content: `确定删除标签 "${labelName}" 吗？`,
    variant: 'error'
  })
  
  if (result.confirmed) {
    try {
      const response = await fetch(apiUrl(`/api/labels/${encodeURIComponent(labelName)}`), {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('后端删除标签失败:', errorData)
      }
    } catch (error) {
      console.error('删除标签请求失败:', error)
      const continueResult = await confirmDialog({
        title: '后端删除失败',
        content: '后端删除标签失败，是否仅在前端移除？刷新后可能会重新出现。',
        variant: 'warning'
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
    setTimeout(() => taskSuccess.value = '', 2000)
  }
}

const updateSelectedLabel = async () => {
  if (!selectedId.value) {
    await alertDialog({
      title: '提示',
      content: '请先选中一个标注',
      variant: 'info'
    })
    return
  }
  
  const annotation = store.annotations.find(ann => ann.id === selectedId.value)
  if (!annotation) return
  
  const result = await promptDialog({
    title: '修改标签',
    content: '请输入新标签名称：',
    placeholder: '标签名称',
    defaultValue: annotation.label,
    variant: 'info'
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
  setTimeout(() => taskSuccess.value = '', 2000)
}

const updateSelectedAnnotationLabel = async () => {
  if (!selectedId.value) return
  
  const newLabel = editingAnnotationLabel.value.trim()
  if (!newLabel) return
  
  const annotation = store.annotations.find(ann => ann.id === selectedId.value)
  if (!annotation) return

  if (!labelColorMap.has(newLabel)) {
    const color = generateColor(newLabel)
    labelColorMap.set(newLabel, color)
    await saveLabelToBackend(newLabel, color)
    syncLabelsFromMap()
  }
  
  annotation.label = newLabel
  annotation.color = labelColorMap.get(newLabel)
  
  currentLabel.value = newLabel
  selectedColor.value = labelColorMap.get(newLabel)
  
  dragTick.value++
  editingAnnotationLabel.value = ''
  taskSuccess.value = `✅ 标注标签已修改为: ${newLabel}`
  setTimeout(() => taskSuccess.value = '', 2000)
}

const updateSelectedAnnotationColor = async () => {
  if (!selectedId.value) {
    await alertDialog({ title: '提示', content: '请先选中一个标注', variant: 'info' })
    return
  }
  
  const annotation = store.annotations.find(ann => ann.id === selectedId.value)
  if (!annotation) return
  
  const newColor = editingAnnotationColor.value
  
  labelColorMap.set(annotation.label, newColor)
  
  store.annotations.forEach(ann => {
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
  
  taskSuccess.value = `✅ 标签 "${annotation.label}" 颜色已修改`
  setTimeout(() => taskSuccess.value = '', 2000)
}

// 修复后的 loadSavedLabels
// ========== 从后端加载标签（完整修复版） ==========
const loadSavedLabels = async () => {
  console.log('📦 [loadSavedLabels] 开始从后端加载标签...')
  
  try {
    const url = apiUrl('/api/labels')
    console.log('🌐 [loadSavedLabels] 请求 URL:', url)
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }
    })
    
    console.log('📥 [loadSavedLabels] 响应状态:', response.status, response.statusText)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [loadSavedLabels] HTTP 错误:', errorText)
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log('📦 [loadSavedLabels] 后端返回数据:', JSON.stringify(data, null, 2))
    
    // 检查是否有警告信息
    if (data.warning) {
      console.warn('⚠️ [loadSavedLabels] 后端警告:', data.warning)
      taskError.value = `⚠️ ${data.warning}`
      setTimeout(() => taskError.value = '', 5000)
    }
    
    // 处理标签数据
    if (data.labels && Array.isArray(data.labels) && data.labels.length > 0) {
      console.log(`✅ [loadSavedLabels] 从后端加载 ${data.labels.length} 个标签`)
      
      // 清空现有标签映射
      labelColorMap.clear()
      
      // 添加每个标签
      data.labels.forEach((label, index) => {
        console.log(`   [${index}] ${label.name}: ${label.color}`)
        
        if (label.name && label.color) {
          labelColorMap.set(label.name, label.color)
        } else {
          console.warn(`   ⚠️ 跳过无效标签:`, label)
        }
      })
      
      // 同步到 labels 数组
      syncLabelsFromMap()
      
      // 设置当前标签为第一个
      if (labels.value.length > 0 && (currentLabel.value === 'object' || !labelColorMap.has(currentLabel.value))) {
        currentLabel.value = labels.value[0].name
        selectedColor.value = labels.value[0].color
        console.log('🎯 [loadSavedLabels] 设置当前标签为:', currentLabel.value)
      }
      
      // 触发刷新
      dragTick.value++
      
    } else {
      console.warn('⚠️ [loadSavedLabels] 后端返回空标签列表，使用默认标签')
      
      // 使用默认标签
      const defaultLabels = [
        { name: 'person', color: '#ff0000' },
        { name: 'car', color: '#0000ff' },
        { name: 'dog', color: '#00ff00' }
      ]
      
      defaultLabels.forEach(label => {
        labelColorMap.set(label.name, label.color)
      })
      
      syncLabelsFromMap()
      currentLabel.value = 'person'
      selectedColor.value = '#ff0000'
    }
    
  } catch (error) {
    console.error('❌ [loadSavedLabels] 加载失败:', error)
    taskError.value = `⚠️ 加载标签失败: ${error.message} (检查后端连接)`
    setTimeout(() => taskError.value = '', 5000)
    
    // 出错时使用默认标签
    console.log('🔄 [loadSavedLabels] 使用默认标签作为备用')
    const defaultLabels = [
      { name: 'person', color: '#ff0000' },
      { name: 'car', color: '#0000ff' },
      { name: 'dog', color: '#00ff00' }
    ]
    
    labelColorMap.clear()
    defaultLabels.forEach(label => {
      labelColorMap.set(label.name, label.color)
    })
    
    syncLabelsFromMap()
    currentLabel.value = 'person'
    selectedColor.value = '#ff0000'
    dragTick.value++
  }
}

const centerImage = () => {
  stageX.value = 0
  stageY.value = 0
  dragTick.value++
}



// ========== 生命周期 ==========
onMounted(async () => {
  const defaultLabels = [
    { name: 'person', color: '#ff0000' },
    { name: 'car', color: '#0000ff' },
    { name: 'dog', color: '#00ff00' }
  ]
  defaultLabels.forEach(label => ensureLabelColor(label.name, label.color))
  syncLabelsFromMap()
  
  await loadSavedLabels()

  let resizeObserver = null
  if (canvasContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      dragTick.value++
    })
    resizeObserver.observe(canvasContainer.value)
  }
  
  if (labelColorMap.has('object')) {
    labelColorMap.delete('object')
  }
  syncLabelsFromMap()
  dragTick.value++
  
  if (!labelColorMap.has(currentLabel.value) || currentLabel.value === 'object') {
    currentLabel.value = labels.value[0]?.name || 'person'
    selectedColor.value = labelColorMap.get(currentLabel.value) || '#ff0000'
  }

  const urlParams = new URLSearchParams(window.location.search)
  let taskId = urlParams.get('task')

  if (!taskId) {
    taskId = localStorage.getItem('lastTaskId')
    if (taskId) {
      window.history.replaceState({}, '', `/app/annotate?task=${taskId}`)
    }
  }

  if (taskId) {
    try {
      const restored = await restoreTask(taskId)
      
      if (restored && store.taskInfo?.imageUrl) {
        syncLabelsFromMap()
        dragTick.value++
        
        if (store.annotations?.length > 0) {
          store.annotations.forEach(ann => {
            const color = labelColorMap.get(ann.label)
            if (color) ann.color = color
          })
          
          const lastAnnotation = store.annotations[store.annotations.length - 1]
          if (lastAnnotation) {
            currentLabel.value = lastAnnotation.label
            selectedColor.value = labelColorMap.get(lastAnnotation.label) || lastAnnotation.color || '#ff0000'
          }
        }
        
        const img = new Image()
        img.crossOrigin = 'anonymous'

        try {
          await new Promise((resolve, reject) => {
            img.onload = () => {
              imageObj.value = img
              resolve()
            }
            img.onerror = () => reject(new Error('图片加载失败'))
            img.src = store.taskInfo.imageUrl
            setTimeout(() => reject(new Error('超时')), 10000)
          })
          
          taskSuccess.value = `✅ 已恢复任务 ${taskId}`
          setTimeout(() => taskSuccess.value = '', 2000)
          
        } catch (imgError) {
          console.error('❌ 原图加载失败:', imgError)
          loadTestImage()
        }
        
      } else {
        loadTestImage()
        localStorage.removeItem('lastTaskId')
      }
      
    } catch (error) {
      console.error('❌ 恢复流程异常:', error)
      loadTestImage()
    }
  } else {
    loadTestImage()
  }

  const globalMouseUpHandler = (e) => {
    if (dialogLock.value) return
    if (e.target?.closest('.dialog-container')) return
    if (isDrawing.value) {
      const mouseUpHandler = handleMouseUp(currentLabel.value)
      mouseUpHandler({ target: stageRef.value?.getNode() })
    }
  }
  
  checkTrainingStatus()
  
  window.addEventListener('mouseup', globalMouseUpHandler)
  window.addEventListener('keydown', handleKeydown, true)
  
  if (canvasContainer.value) {
    canvasContainer.value.addEventListener('wheel', handleWheel, { passive: false })
  }
  
  const handleKeyDown = (e) => {
    if (e.code === 'Space' && !e.repeat) {
      e.preventDefault()
      setSpacePressed(true)
      
      const stageNode = stageRef.value?.getNode()
      if (stageNode && !isPanning.value) {
        stageNode.container().style.cursor = 'grab'
      }
    }
  }
  
  const handleKeyUp = (e) => {
    if (e.code === 'Space') {
      setSpacePressed(false)
      
      const stageNode = stageRef.value?.getNode()
      if (stageNode && !isPanning.value) {
        stageNode.container().style.cursor = 'default'
      }
    }
  }
  
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  
  onUnmounted(() => {
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
</script>

<style scoped>
@import './AnnotateView.css';
</style>