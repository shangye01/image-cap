import { reactive, ref, watch } from 'vue'

export function useColorManager(initialLabels = []) {
  const labelColorMap = reactive(new Map())
  const labels = ref([])
  
  const COLOR_POOL = [
    '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff',
    '#00ffff', '#ff8800', '#8800ff', '#88ff00', '#ff0088',
    '#0088ff', '#888888', '#ffaa00', '#aa00ff', '#aaff00',
    '#ff6600', '#6600ff', '#00ff66', '#ff0066', '#66ff00'
  ]

  const CATEGORY_COLORS = {
    'vehicle': '#0000ff', 'car': '#0000ff', 'truck': '#0000ff',
    'bus': '#0000ff', 'motorcycle': '#0000ff', 'bicycle': '#0000ff',
    'van': '#0000ff', 'suv': '#0000ff', 'trailer': '#0000ff',
    'animal': '#00ff00', 'dog': '#00ff00', 'cat': '#00ff00',
    'bird': '#00ff00', 'horse': '#00ff00', 'sheep': '#00ff00',
    'cow': '#00ff00', 'zebra': '#ffeb3b', 'giraffe': '#ff9800',
    'elephant': '#8b4513', 'bear': '#8b4513', 'panda': '#ff69b4',
    'person': '#ff0000', 'people': '#ff0000', 'man': '#ff0000',
    'woman': '#ff0000', 'child': '#ff4444', 'pedestrian': '#ff0000',
    'traffic light': '#ffff00', 'stop sign': '#ff8800',
    'traffic cone': '#ffa500', 'fire hydrant': '#ff0000',
    'boat': '#00ffff', 'ship': '#00ffff', 'airplane': '#8800ff',
    'helicopter': '#8800ff', 'train': '#ff00ff',
    'chair': '#ffaa00', 'sofa': '#ffaa00', 'bed': '#ffaa00',
    'dining table': '#ffaa00', 'toilet': '#ffaa00', 'tv': '#ffaa00',
    'laptop': '#ffaa00', 'mouse': '#ffaa00', 'remote': '#ffaa00',
    'keyboard': '#ffaa00', 'cell phone': '#ffaa00', 'microwave': '#ffaa00',
    'oven': '#ffaa00', 'toaster': '#ffaa00', 'sink': '#ffaa00',
    'refrigerator': '#ffaa00', 'book': '#ffaa00', 'clock': '#ffaa00',
    'vase': '#ffaa00', 'scissors': '#ffaa00', 'teddy bear': '#ffaa00',
    'hair drier': '#ffaa00', 'toothbrush': '#ffaa00', 'bottle': '#ffaa00',
    'wine glass': '#ffaa00', 'cup': '#ffaa00', 'fork': '#ffaa00',
    'knife': '#ffaa00', 'spoon': '#ffaa00', 'bowl': '#ffaa00',
    'banana': '#ffe135', 'apple': '#ff0000', 'sandwich': '#f5deb3',
    'orange': '#ffa500', 'broccoli': '#228b22', 'carrot': '#ffa500',
    'hot dog': '#ff69b4', 'pizza': '#ffd700', 'donut': '#ff69b4',
    'cake': '#ffb6c1', 'frisbee': '#ff0000', 'skis': '#0000ff',
    'snowboard': '#0000ff', 'sports ball': '#ff0000', 'kite': '#ff69b4',
    'baseball bat': '#8b4513', 'baseball glove': '#8b4513', 'skateboard': '#0000ff',
    'surfboard': '#0000ff', 'tennis racket': '#ff0000', 'backpack': '#8b4513',
    'umbrella': '#9400d3', 'handbag': '#8b4513', 'tie': '#ff0000',
    'suitcase': '#8b4513', 'balloon': '#ff69b4', 'flag': '#ff0000'
  }

  const generateColor = (labelName) => {
    const lowerLabel = labelName.toLowerCase()
    
    for (const [keyword, color] of Object.entries(CATEGORY_COLORS)) {
      if (lowerLabel === keyword || lowerLabel.includes(keyword)) {
        return color
      }
    }

    const usedColors = Array.from(labelColorMap.values())
    const availableColors = COLOR_POOL.filter(c => !usedColors.includes(c))
    
    if (availableColors.length > 0) {
      const hash = labelName.split('').reduce((a, b) => {
        a = ((a << 5) - a) + b.charCodeAt(0)
        return a & a
      }, 0)
      return availableColors[Math.abs(hash) % availableColors.length]
    }

    return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')
  }

  const ensureLabelColor = (labelName, preferredColor = null) => {
    if (!labelName || typeof labelName !== 'string') {
      console.warn('[useColorManager] 无效的标签名:', labelName)
      return '#ff0000'
    }

    const trimmedName = labelName.trim()
    if (!trimmedName) return '#ff0000'

    if (!labelColorMap.has(trimmedName)) {
      const color = preferredColor || generateColor(trimmedName)
      labelColorMap.set(trimmedName, color)
      console.log(`[useColorManager] 新增标签: ${trimmedName} -> ${color}`)
    }
    return labelColorMap.get(trimmedName)
  }

  const syncLabelsFromMap = () => {
    labels.value = Array.from(labelColorMap.entries()).map(([name, color], index) => ({
      id: `label_${index}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      name,
      color
    }))
    labels.value.sort((a, b) => a.name.localeCompare(b.name))
  }

  const updateLabelColor = (labelName, newColor) => {
    if (!labelColorMap.has(labelName)) return false
    labelColorMap.set(labelName, newColor)
    syncLabelsFromMap()
    return true
  }

  const removeLabel = (labelName) => {
    const deleted = labelColorMap.delete(labelName)
    if (deleted) {
      syncLabelsFromMap()
    }
    return deleted
  }

  const getAllLabelNames = () => Array.from(labelColorMap.keys())
  const hasLabel = (name) => labelColorMap.has(name)

  const initLabels = (initialLabels) => {
    if (!Array.isArray(initialLabels)) return
    
    for (const label of initialLabels) {
      const name = label.name || label.label_name
      const color = label.color || label.label_color
      if (name) {
        labelColorMap.set(name, color || generateColor(name))
      }
    }
    syncLabelsFromMap()
  }

  if (initialLabels.length > 0) {
    initLabels(initialLabels)
  }

  watch(() => labelColorMap.size, () => {
    syncLabelsFromMap()
  }, { immediate: false })

  return {
    labelColorMap,
    labels,
    COLOR_POOL,
    generateColor,
    ensureLabelColor,
    syncLabelsFromMap,
    updateLabelColor,
    removeLabel,
    getAllLabelNames,
    hasLabel,
    initLabels,
  }
}