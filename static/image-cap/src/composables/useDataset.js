// src/composables/useDataset.js
import { ref, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 全局状态
const datasets = ref([])
const activeDataset = ref(null)
const loading = ref(false)
const error = ref(null)

export function useDataset() {
  
  // 获取数据集列表
  const fetchDatasets = async () => {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/api/datasets`)
      const data = await res.json()
      datasets.value = data.datasets || []
      activeDataset.value = data.active_dataset_id
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // 切换数据集
  const switchDataset = async (datasetId) => {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.detail || '切换失败')
      activeDataset.value = datasetId
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // 获取当前活动数据集详情
  const fetchActiveDataset = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/datasets/active`)
      return await res.json()
    } catch (err) {
      console.error('获取活动数据集失败:', err)
      return null
    }
  }

  // 启动训练（使用活动数据集或指定数据集）
  const startTraining = async (params) => {
    const {
      projectId,
      datasetId = null,  // 不指定则使用活动数据集
      epochs = 100,
      batch = 16,
      modelSize = 'auto',
      // ... 其他参数
    } = params

    const queryParams = new URLSearchParams({
      project_id: projectId,
      epochs: String(epochs),
      batch: String(batch),
      model_size: modelSize,
      ...(datasetId && { dataset_id: datasetId })
    })

    const res = await fetch(`${API_BASE}/api/training/start?${queryParams}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '训练启动失败')
    }
    
    return await res.json()
  }

  return {
    // 状态
    datasets,
    activeDataset,
    loading,
    error,
    
    // 方法
    fetchDatasets,
    switchDataset,
    fetchActiveDataset,
    startTraining,
    
    // 计算属性
    hasActiveDataset: computed(() => !!activeDataset.value),
    datasetList: computed(() => datasets.value)
  }
}