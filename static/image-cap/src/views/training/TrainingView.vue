<template>
  <div class="training-view">
    <h1>🚀 模型训练中心</h1>
    
    <!-- 数据集状态卡片 -->
    <div class="status-card" :class="{ 'ready': datasetStatus.valid, 'error': !datasetStatus.valid }">
      <h3>📊 数据集状态</h3>
      <p>{{ datasetStatus.message || '点击刷新检查状态' }}</p>
      
      <div v-if="datasetStatus.details && datasetStatus.details.stats" class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">训练集</span>
          <span class="stat-value">{{ datasetStatus.details.stats.train || 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">验证集</span>
          <span class="stat-value">{{ datasetStatus.details.stats.val || 0 }}</span>
        </div>
      </div>

      <div v-if="hardwareInfo.cuda_available" class="gpu-info">
        🎮 GPU: {{ hardwareInfo.cuda_device || '可用' }}
      </div>
      <div v-else class="gpu-info warning">
        ⚠️ 使用CPU训练（较慢）
      </div>
      
      <button @click="checkDataset" :disabled="checking" class="btn btn-secondary">
        {{ checking ? '检查中...' : '刷新状态' }}
      </button>
    </div>

    <!-- 训练配置 -->
    <div class="config-section" v-if="datasetStatus.valid">
      <h3>⚙️ 训练配置</h3>
      
      <div class="form-group">
        <label>训练轮数 (Epochs)</label>
        <input type="number" v-model.number="config.epochs" min="50" max="300" class="input-field">
        <small>建议: 数据少100轮，数据多200轮</small>
      </div>

      <div class="form-group">
        <label>批次大小 (Batch)</label>
        <select v-model.number="config.batch" class="input-field">
          <option :value="8">8 (小显存)</option>
          <option :value="16">16 (推荐)</option>
          <option :value="32">32 (大显存)</option>
        </select>
      </div>

      <div class="form-group">
        <label>模型大小</label>
        <select v-model="config.model_size" class="input-field">
          <option value="auto">🤖 自动选择</option>
          <option value="n">Nano (最快)</option>
          <option value="s">Small</option>
          <option value="m">Medium (平衡)</option>
          <option value="l">Large (准确)</option>
          <option value="x">XLarge (最准)</option>
        </select>
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" v-model="config.augmentation">
          启用数据增强 (推荐)
        </label>
      </div>
      <div class="form-group checkbox">
    <label>
        <input type="checkbox" v-model="config.incremental">
        使用上次训练的模型继续训练（增量训练）
    </label>
</div>
      <button 
        @click="startTraining" 
        :disabled="!datasetStatus.valid || trainingLoading"
        class="btn btn-primary btn-large"
      >
        {{ trainingLoading ? '启动中...' : '🚀 开始训练' }}
      </button>

      <div v-if="trainingMessage" :class="['message', trainingMessage.type]">
        {{ trainingMessage.text }}
      </div>
      
    </div>

    <!-- 上传提示 - 修复版 -->
    <div v-if="trainingStatus.pending_upload && trainingStatus.latest_model" class="upload-prompt">
      <h4>☁️ 模型训练完成</h4>
      <p>版本: {{ trainingStatus.latest_model.version_name || '未知' }}</p>
      <p>mAP50: {{ formatMetric(trainingStatus.latest_model.metrics && trainingStatus.latest_model.metrics.mAP50) }}</p>
      
      <div class="upload-actions">
        <button @click="uploadToCloud" :disabled="uploading" class="btn btn-primary">
          {{ uploading ? '上传中...' : '上传到云端' }}
        </button>
        <button @click="skipUpload" class="btn btn-secondary">
          跳过
        </button>
      </div>
    </div>


    <!-- 模型库 -->
      
        <div class="models-section">
      <h3>🗃️ 模型库</h3>
      <div v-if="models.length === 0" class="empty">
        暂无模型，训练后会显示在这里
      </div>
      <div v-else class="models-list">
        <div 
          v-for="model in models" 
          :key="model.name || model.version_name"
          :class="['model-item', { active: (model.name || model.version_name) === currentModel }]"
        >
          <div class="model-info">
            <span class="model-name">{{ model.displayName || model.name }}</span>
            <span v-if="model.map50" class="model-score">
              mAP50: {{ (model.map50 * 100).toFixed(1) }}%
            </span>
            <!-- 显示云端状态 -->
            <span v-if="model.model_path || model.cloud_path" class="cloud-badge uploaded">☁️ 已上传</span>
            <span v-else class="cloud-badge local">💻 仅本地</span>
          </div>
          <div class="model-actions">
            <button 
              v-if="(model.name || model.version_name) !== currentModel"
              @click="switchModel(model)"
              class="btn btn-small btn-success"
            >
              激活
            </button>
            <span v-else class="current-badge">当前使用</span>
            
            <!-- 上传按钮（仅本地模型显示） -->
            <button 
              v-if="!model.model_path && !model.cloud_path"
              @click="uploadModel(model)"
              :disabled="uploadingModel === (model.name || model.version_name)"
              class="btn btn-small btn-primary"
            >
              {{ uploadingModel === (model.name || model.version_name) ? '上传中...' : '上传云端' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = 'http://localhost:8000/api'
// ✅ 添加这一行在最顶部
let pollInterval = null
// 状态
const datasetStatus = ref({
  valid: false,
  message: '点击刷新检查数据集状态',
  details: null
})
const hardwareInfo = ref({
  cuda_available: false,
  cuda_device: null
})
const checking = ref(false)
const trainingLoading = ref(false)
const trainingMessage = ref(null)
const uploading = ref(false)
const models = ref([])
const currentModel = ref('')

// 训练状态（包含待上传信息）
const trainingStatus = ref({
  pending_upload: false,
  latest_model: null
})

// 配置
const config = ref({
  epochs: 100,
  batch: 16,
  model_size: 'auto',
  augmentation: true
})

// 格式化指标（安全处理null）
const formatMetric = (value) => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

// 检查数据集状态
const checkDataset = async () => {
  checking.value = true
  try {
    const res = await fetch(`${API_BASE}/training/status`)
    const data = await res.json()
    
    // 保存硬件信息
    hardwareInfo.value = {
      cuda_available: data.cuda_available,
      cuda_device: data.cuda_device
    }
    
    // 转换数据格式
    datasetStatus.value = {
      valid: data.dataset_ready || false,
      message: data.dataset_message || (data.dataset_ready ? '✅ 数据集就绪' : '❌ 数据集未准备好'),
      details: {
        stats: data.dataset_stats || {}
      }
    }
    
    // 保存训练状态
    trainingStatus.value = {
      pending_upload: data.pending_upload || false,
      latest_model: data.latest_model || null
    }
    
    // 更新当前模型
    currentModel.value = data.current_model || ''
    
    // ✅ 修复：正确处理云端和本地模型，优先使用云端标记
   // 在 checkDataset 中修改模型显示名称
const localModels = (data.local_models || []).map(m => {
    let displayName = m.name;
    // 如果是 annotation{N} 或 best{N}，添加友好显示
    if (m.name.match(/^(annotation|best)\d+$/)) {
        const num = m.name.replace(/\D/g, '');
        const type = m.name.startsWith('best') ? '🏆 最佳' : '📝 标注';
        displayName = `${type} #${num}`;
    }
    
    return {
        name: m.name,
        displayName: displayName,
        path: m.path,
        is_local: true,
        model_path: null,
        ...m
    };
});
    
    const cloudModels = (data.cloud_models || []).map(m => ({
      name: m.version_name,
      is_cloud: true,
      model_path: m.model_path,  // 云端路径
      ...m
    }))
    
    // ✅ 修复：合并时以云端为准，如果云端有就标记为已上传
    const modelMap = new Map()
    
    // 先添加所有本地模型
    localModels.forEach(lm => {
      modelMap.set(lm.name, { ...lm, model_path: null, is_active: lm.name === currentModel.value })
    })
    
    // 再添加云端模型，覆盖或合并
    cloudModels.forEach(cm => {
      const existing = modelMap.get(cm.name)
      if (existing) {
        // 本地也有，合并数据，标记为已上传
        modelMap.set(cm.name, {
          ...existing,
          model_path: cm.model_path,  // 关键：添加云端路径
          is_cloud: true
        })
      } else {
        // 只有云端有
        modelMap.set(cm.name, { ...cm, is_active: cm.name === currentModel.value })
      }
    })
    
    models.value = Array.from(modelMap.values()).sort((a, b) => {
      const dateA = new Date(a.modified || a.created_at || a.updated_at || 0)
      const dateB = new Date(b.modified || b.created_at || b.updated_at || 0)
      return dateB - dateA
    })
    
  } catch (e) {
    datasetStatus.value = { 
      valid: false, 
      message: '❌ 检查失败: ' + e.message 
    }
  } finally {
    checking.value = false
  }
}

// 开始训练
const startTraining = async () => {
  trainingLoading.value = true
  trainingMessage.value = null
  
  try {
    const params = new URLSearchParams({
      epochs: config.value.epochs,
      batch: config.value.batch,
      model_size: config.value.model_size,
      augmentation: config.value.augmentation
    })
    
    const res = await fetch(`${API_BASE}/training/start?${params}`, {
      method: 'POST'
    })
    const data = await res.json()
    
    if (data.success) {
      trainingMessage.value = {
        type: 'success',
        text: `✅ 训练已启动！模型: ${data.config.model_size}, 轮数: ${data.config.epochs}`
      }
      // 开始轮询状态
      startPolling()
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    trainingMessage.value = {
      type: 'error',
      text: '❌ 启动失败: ' + e.message
    }
  } finally {
    trainingLoading.value = false
  }
}

// 上传到云端
const uploadToCloud = async () => {
  uploading.value = true
  try {
    const res = await fetch(`${API_BASE}/models/upload`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      alert('✅ ' + data.message)
      checkDataset() // 刷新状态
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    alert('❌ 上传失败: ' + e.message)
  } finally {
    uploading.value = false
  }
}

// 跳过上传
const skipUpload = async () => {
  try {
    await fetch(`${API_BASE}/models/skip-upload`, { method: 'POST' })
    checkDataset()
  } catch (e) {
    console.error(e)
  }
}

// 切换模型
const switchModel = async (model) => {
  const modelName = model.name || model.version_name
  
  try {
    // 防止重复点击
    if (model.is_active || modelName === currentModel.value) {
      return
    }
    
    const path = model.path || model.local_path
    if (!path) {
      alert('❌ 模型路径不存在')
      return
    }
    
    // 立即更新前端状态（乐观更新）
    const previousModel = currentModel.value
    currentModel.value = modelName
    
    // 更新模型列表
    models.value = models.value.map(m => {
      const mName = m.name || m.version_name
      return {
        ...m,
        is_active: mName === modelName
      }
    })
    
    // 调用后端API
    const res = await fetch(`${API_BASE}/models/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, name: modelName })
    })
    
    const data = await res.json()
    
    if (!data.success) {
      // 失败时恢复状态
      currentModel.value = previousModel
      models.value = models.value.map(m => ({
        ...m,
        is_active: (m.name || m.version_name) === previousModel
      }))
      throw new Error(data.message || '切换失败')
    }
    
    console.log('✅ 已激活模型:', modelName)
    
  } catch (e) {
    alert('❌ 切换失败: ' + e.message)
  }
}

const startPolling = () => {
  // ✅ 先清除旧的
  if (pollInterval) clearInterval(pollInterval)
  
  pollInterval = setInterval(() => {
    checkDataset()
  }, 5000)
  
  setTimeout(() => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }, 30000)
}


// 在 uploading 变量下面添加
const uploadingModel = ref('')  // 记录正在上传的模型名称

// 添加上传方法
const uploadModel = async (model) => {
  const modelName = model.name || model.version_name
  uploadingModel.value = modelName
  
  try {
    // 使用 encodeURIComponent 处理特殊字符
    const encodedName = encodeURIComponent(modelName)
    
    const res = await fetch(`${API_BASE}/models/${encodedName}/upload`, {
      method: 'POST'
    })
    
    // 检查响应状态
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP ${res.status}`)
    }
    
    const data = await res.json()
    
    if (data.success) {
      alert(`✅ ${data.message}\n大小: ${data.size_mb} MB`)
      checkDataset() // 刷新列表
    } else {
      throw new Error(data.message || '上传失败')
    }
  } catch (e) {
    alert('❌ 上传失败: ' + e.message)
  } finally {
    uploadingModel.value = ''
  }
}

// 生命周期
onMounted(() => {
  checkDataset()
})


</script>

<style scoped>
.training-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  margin-bottom: 30px;
  color: #2c3e50;
}

.status-card {
  background: #ffebee;
  border: 1px solid #ef5350;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.status-card.ready {
  background: #e8f5e9;
  border-color: #66bb6a;
}

.status-card h3 {
  margin-top: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin: 15px 0;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background: rgba(255,255,255,0.5);
  border-radius: 8px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #666;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
}

.gpu-info {
  padding: 10px;
  background: #e3f2fd;
  border-radius: 6px;
  margin: 10px 0;
  font-size: 14px;
}

.gpu-info.warning {
  background: #fff3e0;
  color: #e65100;
}

.config-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
}

.input-field {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-group small {
  color: #666;
  font-size: 12px;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-secondary {
  background: #757575;
  color: white;
}

.btn-success {
  background: #4caf50;
  color: white;
}

.btn-large {
  width: 100%;
  padding: 15px;
  font-size: 16px;
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
}

.message {
  padding: 12px;
  border-radius: 6px;
  margin-top: 15px;
}

.message.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.message.error {
  background: #ffebee;
  color: #c62828;
}

/* 上传提示样式 */
.upload-prompt {
  background: #e3f2fd;
  border: 2px solid #2196f3;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.upload-prompt h4 {
  margin-top: 0;
  color: #1565c0;
}

.upload-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.models-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.models-list {
  margin-top: 15px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 8px;
}

.model-item.active {
  background: #e3f2fd;
  border: 1px solid #2196f3;
}

.model-info {
  display: flex;
  flex-direction: column;
}

.model-name {
  font-weight: 600;
}

.model-score {
  font-size: 12px;
  color: #666;
}

.current-badge {
  background: #4caf50;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.empty {
  text-align: center;
  color: #999;
  padding: 40px;
}

/* 添加在 style 部分末尾 */

.model-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cloud-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 8px;
}

.cloud-badge.uploaded {
  background: #e3f2fd;
  color: #1565c0;
}

.cloud-badge.local {
  background: #f5f5f5;
  color: #666;
}

.btn-primary {
  background: #2196f3;
  color: white;
}
</style>