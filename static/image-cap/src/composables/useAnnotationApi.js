// composables/useAnnotationApi.js

import { ref } from 'vue'
import { predictAnnotations } from '@/api/annotation'

export function useAnnotationApi(
  containerSize,
  store,
  imageObj,
  labelColorMap,
  taskError,
  taskSuccess,
  currentLabel,
  labels,
  ensureLabelColor
) {
  const predicting = ref(false)

  const syncLabelsFromMap = () => {
    if (!labels || !labels.value) return
    
    labels.value = Array.from(labelColorMap.entries())
      .filter(([name]) => name !== 'object')
      .map(([name, color], index) => ({
        id: `map_${index}_${Date.now()}`,
        name,
        color  // 这里从 labelColorMap 获取颜色
      }))
  }

  const postProcessResults = (results, srcWidth, srcHeight, origWidth, origHeight) => {
    if (!results || results.length === 0) return []
    const scaleX = origWidth / srcWidth
    const scaleY = origHeight / srcHeight
    results.forEach(ann => {
      ann.x *= scaleX
      ann.y *= scaleY
      ann.width *= scaleX
      ann.height *= scaleY
    })
    results.forEach(ann => {
      ann.x = Math.max(0, Math.min(ann.x, origWidth - ann.width))
      ann.y = Math.max(0, Math.min(ann.y, origHeight - ann.height))
      ann.width = Math.min(ann.width, origWidth - ann.x)
      ann.height = Math.min(ann.height, origHeight - ann.y)
    })
    // ✅ 放宽最小尺寸限制（从 20 改为 10）
    const minSize = 10
    return results.filter(ann => ann.width > minSize && ann.height > minSize)
  }

  const predictAnnotationsWithRetry = async (formData, maxRetries = 2) => {
    for (let i = 0; i <= maxRetries; i++) {
      try {
        // ✅ 现在 predictAnnotations 会直接返回数组或抛出错误
        const annotations = await predictAnnotations(formData)
        return annotations  // 直接返回数组
        
      } catch (error) {
        console.error(`尝试 ${i + 1}/${maxRetries + 1} 失败:`, error.message)
        
        // 如果是最后一次尝试，抛出错误
        if (i === maxRetries) {
          throw error
        }
        
        // 指数退避重试
        const delay = 1000 * Math.pow(2, i)
        console.log(`⏳ ${delay}ms 后重试...`)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }
  

  // ✅ 完整的 runSmartAnnotation 函数
  
const runSmartAnnotation = async () => {
  if (!imageObj.value) {
    alert('请先加载图片')
    return
  }
  
  predicting.value = true
  taskError.value = ''
  taskSuccess.value = '🔍 正在识别，请稍候...'

  try {
    const img = imageObj.value
    const MAX_SIZE = 1280
    let width = img.width
    let height = img.height

    console.log('🖼️ 原始图片尺寸:', { width: img.width, height: img.height })

    // 缩放图片（保持宽高比）
    if (width > MAX_SIZE || height > MAX_SIZE) {
      const ratio = Math.min(MAX_SIZE / width, MAX_SIZE / height)
      width = Math.floor(width * ratio)
      height = Math.floor(height * ratio)
      console.log('📐 缩放后尺寸:', { width, height, ratio })
    }

    // 创建离屏画布
    const canvas = new OffscreenCanvas(width, height)
    const ctx = canvas.getContext('2d', { willReadFrequently: false, alpha: false })
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(img, 0, 0, width, height)

    // 转换为 blob
    const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.9 })
    console.log('📦 图片blob大小:', (blob.size / 1024).toFixed(2), 'KB')
    
    const formData = new FormData()
    formData.append('file', blob, 'image.jpg')

    console.log('📤 发送识别请求...')
    
    // ✅ 调用API（现在会抛出详细错误）
    const annotations = await predictAnnotationsWithRetry(formData)
    
    console.log('📥 收到标注数量:', annotations.length)
    console.log('📋 标注数据:', annotations)
    
    // ✅ 检查是否为空数组（后端正常返回但没有检测到目标）
    if (annotations.length === 0) {
      taskSuccess.value = ''
      taskError.value = '⚠️ AI未检测到目标\n\n可能原因：\n1. 图片中无 recognizable 对象\n2. 后端置信度阈值过高\n3. 模型未正确加载\n\n请检查后端控制台日志'
      setTimeout(() => taskError.value = '', 8000)
      return
    }
    
    // 后处理：缩放坐标回原图尺寸
    const processedResults = postProcessResults(annotations, width, height, img.width, img.height)
    
    console.log('🎯 后处理后数量:', processedResults.length)
    
    if (processedResults.length === 0) {
      taskSuccess.value = ''
      taskError.value = '⚠️ 检测到目标但尺寸太小被过滤'
      setTimeout(() => taskError.value = '', 5000)
      return
    }
    
    // 清空旧标注
    store.clearAnnotations()
    
    // 处理标签颜色
    const newLabels = [...new Set(processedResults.map(ann => ann.label))]
    newLabels.forEach(label => {
      if (!labelColorMap.has(label)) {
        ensureLabelColor(label)
      }
    })
    syncLabelsFromMap()
    
    // 添加标注
    processedResults.forEach((ann, index) => {
      const annotationData = {
        id: ann.id || `ai_${Date.now()}_${index}`,
        x: ann.x,
        y: ann.y,
        width: ann.width,
        height: ann.height,
        label: ann.label,
        confidence: ann.confidence,
        color: ann.color || labelColorMap.get(ann.label) || '#ff0000'
      }
      
      store.addAnnotation(annotationData)
      
      if (index === 0) {
        store.selectedId = annotationData.id
        currentLabel.value = ann.label
      }
    })
    
    taskSuccess.value = `✅ 成功添加 ${processedResults.length} 个智能标注`
    setTimeout(() => taskSuccess.value = '', 3000)
    
  } catch (error) {
    // ✅ 现在能捕获到详细的错误信息了
    console.error('❌ 智能标注失败:', error)
    taskSuccess.value = ''
    taskError.value = `识别失败: ${error.message}`
    setTimeout(() => taskError.value = '', 8000)
  } finally {
    predicting.value = false
  }
}

  return {
    predicting,
    runSmartAnnotation
  }
}