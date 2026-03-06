<template>
  <div class="canvas-container">
    <v-stage
      ref="stageRef"
      :config="stageConfig"
      @mousedown="handleStageMouseDown"
    >
      <v-layer>
        <!-- 背景图片 - 使用 maxWidth/maxHeight 限制 -->
        <v-image 
          v-if="imageUrl" 
          :config="imageConfig"
        />
        
        <!-- 标注矩形框 -->
        <v-rect
          v-for="ann in annotations"
          :key="ann.id"
          :config="{
            ...ann,
            id: ann.id,
            stroke: ann.color || '#ff0000',
            strokeWidth: selectedId === ann.id ? 3 : 2,
            fill: 'rgba(0,0,0,0)',
            draggable: true,
          }"
          @click="selectAnnotation(ann.id)"
          @dragend="handleDragEnd($event, ann.id)"
        />
        
        <!-- 变换控制器 -->
        <v-transformer 
          v-if="selectedNode"
          ref="transformerRef"
          :config="transformerConfig"
        />
      </v-layer>
    </v-stage>

    <!-- 当前状态提示 -->
    <div class="status-bar">
      <span v-if="!imageUrl">请加载图片</span>
      <span v-else>尺寸: {{ imageSize.width }}×{{ imageSize.height }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAnnotationStore } from '@/stores/annotation'
import { predictAnnotations } from '@/api/annotation'

const store = useAnnotationStore()
const stageRef = ref(null)
const transformerRef = ref(null)
const predicting = ref(false)

// 图片原始尺寸
const imageSize = ref({ width: 0, height: 0 })

// 画布配置 - 自动适应图片
const stageConfig = computed(() => ({
  width: imageSize.value.width || 800,
  height: imageSize.value.height || 600,
  draggable: false
}))

// 图片配置 - 自适应缩放
const imageConfig = computed(() => {
  if (!imageUrl.value || !imageObj.value) return {}
  
  // 如果图片过大，等比缩放
  const maxWidth = window.innerWidth * 0.6
  const maxHeight = window.innerHeight * 0.8
  
  let width = imageSize.value.width
  let height = imageSize.value.height
  
  if (width > maxWidth || height > maxHeight) {
    const ratio = Math.min(maxWidth / width, maxHeight / height)
    width = width * ratio
    height = height * ratio
  }
  
  return {
    image: imageObj.value,
    x: 0,
    y: 0,
    width,
    height
  }
})

// 图片对象
const imageObj = ref(null)

// 计算属性
const annotations = computed(() => store.annotations)
const selectedId = computed(() => store.selectedId)
const imageUrl = computed(() => store.imageUrl)

// 监听图片URL变化
watch(imageUrl, (newUrl) => {
  if (newUrl) {
    const img = new Image()
    img.onload = () => {
      imageObj.value = img
      imageSize.value = { width: img.width, height: img.height }
      console.log('🖼️ 图片加载完成:', imageSize.value)
    }
    img.onerror = () => {
      console.error('❌ 图片加载失败:', newUrl)
      alert('图片加载失败')
    }
    img.src = newUrl
  } else {
    imageObj.value = null
    imageSize.value = { width: 0, height: 0 }
  }
})



// 智能识别
const handlePredict = async () => {
  if (!imageUrl.value) {
    alert('请先加载图片！')
    return
  }
  
  predicting.value = true
  console.log('🤖 开始智能识别...')
  
  try {
    const blob = await fetch(imageUrl.value).then(r => r.blob())
    const file = new File([blob], 'image.jpg', { type: blob.type })
    
    const newAnnotations = await predictAnnotations(file)
    const safeAnnotations = Array.isArray(newAnnotations) ? newAnnotations : []
    
    console.log(`✅ 识别完成: ${safeAnnotations.length} 个目标`)
    
    if (safeAnnotations.length === 0) {
      alert('未检测到目标')
    }
    
    store.setAnnotations(safeAnnotations)
  } catch (error) {
    console.error('❌ 识别失败:', error)
    alert(`识别失败: ${error.message}`)
    store.setAnnotations([])
  } finally {
    predicting.value = false
  }
}

defineExpose({ handlePredict })
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-bar {
  padding: 8px 15px;
  background: #f0f2f5;
  font-size: 12px;
  color: #666;
  border-radius: 4px;
}
</style>