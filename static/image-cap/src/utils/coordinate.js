// src/utils/coordinate.js
// 统一的坐标转换工具

/**
 * 判断坐标是否为归一化格式（0-1范围）
 */
export function isNormalized(ann) {
  // 如果所有坐标都 <= 1，认为是归一化坐标
  return ann.x <= 1 && ann.y <= 1 && ann.width <= 1 && ann.height <= 1
}

/**
 * 归一化坐标 → 像素坐标
 * @param {Object} ann - 标注对象
 * @param {number} imgWidth - 原图宽度
 * @param {number} imgHeight - 原图高度
 * @returns {Object} 像素坐标标注
 */
export function normalizedToPixel(ann, imgWidth, imgHeight) {
  return {
    ...ann,
    x: ann.x * imgWidth,
    y: ann.y * imgHeight,
    width: ann.width * imgWidth,
    height: ann.height * imgHeight,
    original_width: imgWidth,
    original_height: imgHeight,
  }
}

/**
 * 像素坐标 → 归一化坐标
 * @param {Object} ann - 标注对象
 * @param {number} imgWidth - 原图宽度
 * @param {number} imgHeight - 原图高度
 * @returns {Object} 归一化坐标标注
 */
export function pixelToNormalized(ann, imgWidth, imgHeight) {
  return {
    ...ann,
    x: ann.x / imgWidth,
    y: ann.y / imgHeight,
    width: ann.width / imgWidth,
    height: ann.height / imgHeight,
    original_width: imgWidth,
    original_height: imgHeight,
  }
}

/**
 * 像素坐标 → 容器坐标（用于画布显示）
 * @param {Object} ann - 标注对象（像素坐标）
 * @param {number} containerScale - 容器缩放比例
 * @returns {Object} 容器坐标标注
 */
export function pixelToContainer(ann, containerScale) {
  return {
    ...ann,
    x: ann.x * containerScale,
    y: ann.y * containerScale,
    width: ann.width * containerScale,
    height: ann.height * containerScale,
  }
}

/**
 * 容器坐标 → 像素坐标
 * @param {Object} ann - 标注对象（容器坐标）
 * @param {number} containerScale - 容器缩放比例
 * @returns {Object} 像素坐标标注
 */
export function containerToPixel(ann, containerScale) {
  return {
    ...ann,
    x: ann.x / containerScale,
    y: ann.y / containerScale,
    width: ann.width / containerScale,
    height: ann.height / containerScale,
  }
}

/**
 * 统一的标注转换：后端存储格式 → 前端显示格式
 * 后端存储的是归一化坐标，需要根据当前图片尺寸转换为容器坐标
 * 
 * @param {Object} ann - 后端返回的标注
 * @param {Object} options - 转换选项
 * @param {number} options.currentWidth - 当前图片实际宽度
 * @param {number} options.currentHeight - 当前图片实际高度
 * @param {number} options.savedWidth - 保存标注时的原图宽度（从ann.original_width获取）
 * @param {number} options.savedHeight - 保存标注时的原图高度
 * @param {number} options.containerScale - 画布容器缩放比例
 * @returns {Object} 转换后的标注（容器坐标）
 */
export function backendToDisplay(ann, options) {
  const {
    currentWidth,
    currentHeight,
    savedWidth = ann.original_width || currentWidth,
    savedHeight = ann.original_height || currentHeight,
    containerScale = 1,
  } = options

  // 步骤1：判断输入坐标类型
  const normalized = isNormalized(ann)
  
  let pixelX, pixelY, pixelW, pixelH
  
  if (normalized) {
    // 归一化 → 保存时的像素 → 当前像素
    const savedPixelX = ann.x * savedWidth
    const savedPixelY = ann.y * savedHeight
    const savedPixelW = ann.width * savedWidth
    const savedPixelH = ann.height * savedHeight
    
    // 缩放到当前实际尺寸
    const widthRatio = currentWidth / savedWidth
    const heightRatio = currentHeight / savedHeight
    
    pixelX = savedPixelX * widthRatio
    pixelY = savedPixelY * heightRatio
    pixelW = savedPixelW * widthRatio
    pixelH = savedPixelH * heightRatio
  } else {
    // 已经是像素坐标，直接缩放到当前尺寸
    const widthRatio = currentWidth / savedWidth
    const heightRatio = currentHeight / savedHeight
    
    pixelX = ann.x * widthRatio
    pixelY = ann.y * heightRatio
    pixelW = ann.width * widthRatio
    pixelH = ann.height * heightRatio
  }
  
  // 步骤2：像素 → 容器坐标
  return {
    ...ann,
    x: pixelX * containerScale,
    y: pixelY * containerScale,
    width: pixelW * containerScale,
    height: pixelH * containerScale,
    original_width: currentWidth,
    original_height: currentHeight,
  }
}

/**
 * 前端显示格式 → 后端存储格式（归一化坐标）
 * 
 * @param {Object} ann - 前端标注（容器坐标）
 * @param {Object} options - 转换选项
 * @param {number} options.containerScale - 容器缩放比例
 * @param {number} options.imgWidth - 原图宽度
 * @param {number} options.imgHeight - 原图高度
 * @returns {Object} 归一化坐标标注
 */
export function displayToBackend(ann, options) {
  const { containerScale = 1, imgWidth, imgHeight } = options
  
  // 步骤1：容器 → 像素
  const pixelX = ann.x / containerScale
  const pixelY = ann.y / containerScale
  const pixelW = ann.width / containerScale
  const pixelH = ann.height / containerScale
  
  // 步骤2：像素 → 归一化
  return {
    ...ann,
    x: pixelX / imgWidth,
    y: pixelY / imgHeight,
    width: pixelW / imgWidth,
    height: pixelH / imgHeight,
    original_width: imgWidth,
    original_height: imgHeight,
  }
}

/**
 * 计算图片在固定尺寸容器中的显示尺寸（保持宽高比居中）
 * @param {number} imgWidth - 图片宽度
 * @param {number} imgHeight - 图片高度
 * @param {number} containerSize - 容器尺寸（正方形）
 * @returns {Object} { width, height, scale, offsetX, offsetY }
 */
export function calculateThumbDisplay(imgWidth, imgHeight, containerSize = 220) {
  const scale = Math.min(containerSize / imgWidth, containerSize / imgHeight)
  const width = imgWidth * scale
  const height = imgHeight * scale
  const offsetX = (containerSize - width) / 2
  const offsetY = (containerSize - height) / 2
  
  return { width, height, scale, offsetX, offsetY }
}