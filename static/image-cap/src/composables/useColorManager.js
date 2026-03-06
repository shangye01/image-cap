import { reactive, ref } from 'vue'

export function useColorManager(initialLabels = []) {
  const labelColorMap = reactive(new Map())
  const labels = ref([])
  
  const COLOR_POOL = [
    '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff',
    '#00ffff', '#ff8800', '#8800ff', '#88ff00', '#ff0088',
    '#0088ff', '#888888', '#ffaa00', '#aa00ff', '#aaff00'
  ]

  const generateColor = (labelName) => {
    const categoryColors = {
      'vehicle': '#0000ff', 'car': '#0000ff', 'truck': '#0000ff',
      'bus': '#0000ff', 'motorcycle': '#0000ff', 'bicycle': '#0000ff',
      'animal': '#00ff00', 'dog': '#00ff00', 'cat': '#00ff00',
      'bird': '#00ff00', 'horse': '#00ff00', 'sheep': '#00ff00',
      'cow': '#00ff00',
      'person': '#ff0000', 'people': '#ff0000',
      'traffic light': '#ffff00', 'stop sign': '#ff8800',
      'boat': '#00ffff', 'airplane': '#8800ff',
      'train': '#ff00ff', 'chair': '#ffaa00'
    }

    const lowerLabel = labelName.toLowerCase()
    for (const [keyword, color] of Object.entries(categoryColors)) {
      if (lowerLabel.includes(keyword)) return color
    }

    const usedColors = Array.from(labelColorMap.values())
    for (const color of COLOR_POOL) {
      if (!usedColors.includes(color)) return color
    }

    return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')
  }

  const ensureLabelColor = (labelName, preferredColor = null) => {
    if (!labelColorMap.has(labelName)) {
      const color = preferredColor || generateColor(labelName)
      labelColorMap.set(labelName, color)
    }
    return labelColorMap.get(labelName)
  }

  // ✅ **修复：同步时彻底删除 object 标签**
  const syncLabelsFromMap = () => {
    if (!labels || !labels.value) return
    
    // ✅ 删除 object 标签
    labelColorMap.delete('object')
    
    labels.value = Array.from(labelColorMap.entries())
      .filter(([name]) => name !== 'object')
      .map(([name, color], index) => ({
        id: `map_${index}_${Date.now()}`,
        name,
        color
      }))
  }

  const initLabels = (initialLabels) => {
    initialLabels.forEach(label => {
      ensureLabelColor(label.name, label.color)
    })
    // ✅ 删除 object
    labelColorMap.delete('object')
    syncLabelsFromMap()
  }

  if (initialLabels.length > 0) {
    initLabels(initialLabels)
  }

  return {
    labelColorMap,
    COLOR_POOL,
    generateColor,
    ensureLabelColor,
    syncLabelsFromMap,
    labels
  }
}