<template>
  <div class="training-view">
    <GradientBackground />
    
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>

    <div class="content-wrapper">
      
      <!-- 全局错误提示 - 放在最顶部，始终可见 -->
      <div v-if="globalError" class="global-error-banner" @click="clearGlobalError">
        <div class="error-icon">❌</div>
        <span>{{ globalError }}</span>
        <button class="error-close" @click.stop="clearGlobalError">✕</button>
      </div>
      
     

      <!-- 数据集选择器 - 新增 -->
            <!-- 数据集选择器 - 新增 -->
      <div class="glass-card dataset-selector-card">
        <div class="card-header">
          <div class="icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
              <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
          </div>
          <h3>数据集选择</h3>
          <span v-if="datasetTotal > 0" class="dataset-count-badge">{{ datasetTotal }} 个</span>
        </div>
        
        <!-- 搜索框 -->
        <div class="dataset-search">
          <input 
            v-model="datasetSearch" 
            @input="searchDatasets"
            type="text" 
            placeholder="搜索数据集..." 
            class="dataset-search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        
        <!-- 数据集列表 - 限制高度可滚动 -->
        <div class="dataset-list-container">
          <div class="dataset-list">
            <div 
              v-for="dataset in availableDatasets" 
              :key="dataset.id || dataset.dataset_id"
              :class="['dataset-item', { 
                active: selectedDatasetId === (dataset.id || dataset.dataset_id),
                cached: dataset.cached,
                'is-base': dataset.is_base
              }]"
              @click="selectDataset(dataset.id || dataset.dataset_id)"
            >
              <div class="dataset-main">
                <div class="dataset-icon">
                  <span v-if="dataset.is_base">🏠</span>
                  <span v-else-if="dataset.cached">💾</span>
                  <span v-else>☁️</span>
                </div>
                <div class="dataset-info">
                  <span class="dataset-name">{{ dataset.name || dataset.dataset_name || dataset.id || '未命名' }}</span>
                  <div class="dataset-meta">
                    <span v-if="dataset.is_base" class="cache-tag base">基础</span>
                    <span v-else-if="dataset.cached" class="cache-tag local">已缓存</span>
                    <span v-else class="cache-tag cloud">云端</span>
                    <span v-if="dataset.stats" class="stats-tag">
                      {{ dataset.stats.train_images || dataset.stats.train || 0 }} 训练 / 
                      {{ dataset.stats.val_images || dataset.stats.val || 0 }} 验证
                      <span v-if="dataset.stats.train_has_more || dataset.stats.val_has_more" class="more-hint">+</span>
                    </span>
                  </div>
                </div>
              </div>
              <div class="dataset-status">
                <svg v-if="selectedDatasetId === (dataset.id || dataset.dataset_id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            </div>
          </div>
          
          <!-- 加载更多 -->
          <div v-if="datasetHasMore" class="load-more">
            <button @click="loadMoreDatasets" class="btn btn-ghost btn-load-more">
              加载更多 ({{ datasetTotal - availableDatasets.length }} 个)
            </button>
          </div>
        </div>
        
        <div v-if="availableDatasets.length === 0" class="empty-datasets">
          <p>暂无可用数据集</p>
          <span>请在 Supabase Storage 的 datasets bucket 中上传数据</span>
        </div>
      </div>

      <!-- 数据集状态卡片 - 只展示元数据，不下载 -->
      <div class="glass-card status-card" :class="{ 'ready': datasetStatus.valid, 'error': !datasetStatus.valid }">
        <div class="card-header">
          <div class="icon-wrapper">
            <svg v-if="datasetStatus.valid" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <h3>数据集状态</h3>
          <div class="status-badge" :class="datasetStatus.valid ? 'success' : 'warning'">
            {{ datasetStatus.valid ? '云端就绪' : '待准备' }}
          </div>
        </div>
        
        <!-- 数据集状态卡片中的 status-message 添加错误样式 -->
<p class="status-message" :class="{ 'error-text': !datasetStatus.valid }">
  {{ datasetStatus.message || '数据集存储在云端，训练时自动下载' }}
</p>
        
        <!-- 数据集元数据展示 -->
        <div v-if="datasetStatus.details && datasetStatus.details.stats" class="stats-grid">
          <div class="stat-item">
            <div class="stat-icon train">🎯</div>
            <span class="stat-value">{{ datasetStatus.details.stats.train || 0 }}</span>
            <span class="stat-label">训练集样本</span>
          </div>
          <div class="stat-item">
            <div class="stat-icon val">✅</div>
            <span class="stat-value">{{ datasetStatus.details.stats.val || 0 }}</span>
            <span class="stat-label">验证集样本</span>
          </div>
          <div class="stat-item">
            <div class="stat-icon classes">🏷️</div>
            <span class="stat-value">{{ datasetStatus.details.stats.classes || 0 }}</span>
            <span class="stat-label">类别数</span>
          </div>
        </div>

        <!-- 缓存状态 -->
        <div v-if="cacheStatus.cached" class="cache-info">
          <div class="cache-badge success">
            <span>💾</span>
            <span>已缓存到本地，可直接训练</span>
          </div>
        </div>
        <div v-else-if="datasetStatus.valid" class="cache-info">
          <div class="cache-badge">
            <span>☁️</span>
            <span>存储在云端，训练时自动下载</span>
          </div>
        </div>

        <div class="hardware-info">
          <div v-if="hardwareInfo.cuda_available" class="gpu-badge">
            <span class="gpu-icon">🚀</span>
            <span>GPU 加速: {{ hardwareInfo.cuda_device || '可用' }}</span>
          </div>
          <div v-else class="gpu-badge warning">
            <span class="gpu-icon">⚡</span>
            <span>CPU 模式（训练较慢）</span>
          </div>
        </div>
      </div>

      <!-- 数据集下载进度面板 - 训练前展示 -->
      <div v-if="downloadProgress.show" class="glass-card download-progress-card">
        <div class="card-header">
          <div class="icon-wrapper download-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3>正在下载数据集</h3>
        </div>

        <div class="download-progress-content">
          <div class="progress-header">
            <div class="progress-icon" :class="downloadProgress.status">
              <span v-if="downloadProgress.status === 'downloading'">⬇️</span>
              <span v-else-if="downloadProgress.status === 'completed'">✅</span>
              <span v-else-if="downloadProgress.status === 'error'">❌</span>
            </div>
            <div class="progress-title-group">
              <h4 class="progress-title">{{ downloadProgress.message }}</h4>
              <p class="progress-subtitle">{{ downloadProgress.detail }}</p>
            </div>
            <div class="progress-percentage">{{ downloadProgress.percent }}%</div>
          </div>

          <div class="progress-bar-container">
            <div class="progress-track">
              <div 
                class="progress-fill" 
                :class="downloadProgress.status"
                :style="{ width: downloadProgress.percent + '%' }"
              >
                <div class="progress-shine"></div>
              </div>
            </div>
          </div>

          <!-- 下载步骤 -->
          <div class="download-steps">
            <div 
              v-for="(step, index) in downloadSteps" 
              :key="index"
              class="download-step"
              :class="{
                'completed': step.completed,
                'active': step.active,
                'pending': !step.completed && !step.active
              }"
            >
              <div class="step-dot">
                <svg v-if="step.completed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span v-else-if="step.active" class="step-spinner"></span>
                <span v-else>{{ index + 1 }}</span>
              </div>
              <span class="step-name">{{ step.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 上传数据集卡片 -->
      <div class="glass-card upload-dataset-card">
        <div class="card-header">
          <div class="icon-wrapper upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div class="header-text">
            <h3>上传本地数据集</h3>
            <p class="header-desc">请将数据集压缩为 ZIP 格式上传（包含 images/ 和 labels/）</p>
          </div>
        </div>
        
        <!-- 上传区域 -->
        <div class="upload-area" v-if="!uploadState.isProcessing">
          <input 
            type="file" 
            ref="zipInput"
            accept=".zip"
            @change="handleZipSelect"
            style="display: none"
          />
          
          <div 
            class="drop-zone" 
            @click="$refs.zipInput.click()"
            @dragover.prevent
            @drop.prevent="handleZipDrop"
            :class="{ 'dragging': isDragging }"
            @dragenter="isDragging = true"
            @dragleave="isDragging = false"
          >
            <div class="drop-zone-inner">
              <div class="drop-illustration">
                <div class="upload-circle">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <div class="pulse-ring"></div>
              </div>
              
              <div class="drop-text">
                <p class="drop-title">点击选择 ZIP 文件</p>
                <p class="drop-subtitle">或拖拽 ZIP 文件到此处</p>
              </div>
              
              <div class="drop-format">
                <span class="format-tag">YOLO 格式 ZIP</span>
                <span class="format-divider">|</span>
                <span class="format-tag">最大 2GB</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 文件信息 -->
        <div v-if="selectedZip && !uploadState.isProcessing" class="zip-info">
          <div class="zip-icon">📦</div>
          <div class="zip-details">
            <span class="zip-name">{{ selectedZip.name }}</span>
            <span class="zip-size">{{ formatFileSize(selectedZip.size) }}</span>
          </div>
          <button @click="selectedZip = null" class="zip-remove">✕</button>
        </div>

        <!-- 详细进度面板 -->
        <div v-if="uploadState.isProcessing" class="progress-panel">
          <div class="progress-header">
            <div class="progress-icon" :class="uploadState.stage">
              <span v-if="uploadState.stage === 'uploading'">⬆️</span>
              <span v-else-if="uploadState.stage === 'processing'">⚙️</span>
              <span v-else-if="uploadState.stage === 'completed'">✅</span>
              <span v-else-if="uploadState.stage === 'error'">❌</span>
            </div>
            <div class="progress-title-group">
              <h4 class="progress-title">{{ uploadState.title }}</h4>
              <p class="progress-subtitle">{{ uploadState.message }}</p>
            </div>
            <div class="progress-percentage">{{ uploadState.percent }}%</div>
          </div>

          <!-- 主进度条 -->
          <div class="progress-bar-container">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: uploadState.percent + '%' }" :class="uploadState.stage">
                <div class="progress-shine"></div>
              </div>
            </div>
          </div>

          <!-- 详细步骤 -->
          <div class="progress-steps">
            <div 
              v-for="(step, index) in uploadSteps" 
              :key="index"
              class="progress-step"
              :class="{
                'completed': step.status === 'completed',
                'active': step.status === 'active',
                'pending': step.status === 'pending',
                'error': step.status === 'error'
              }"
            >
              <div class="step-indicator">
                <div class="step-dot">
                  <svg v-if="step.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  <span v-else-if="step.status === 'active'" class="step-spinner"></span>
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <div v-if="index < uploadSteps.length - 1" class="step-line"></div>
              </div>
              <div class="step-content">
                <span class="step-name">{{ step.name }}</span>
                <span class="step-desc">{{ step.desc }}</span>
                <span v-if="step.detail" class="step-detail">{{ step.detail }}</span>
              </div>
            </div>
          </div>

          <!-- 实时日志 -->
          <div v-if="uploadLogs.length > 0" class="progress-logs">
            <div class="logs-header">
              <span>📋 处理日志</span>
              <button @click="uploadLogs = []" class="clear-logs">清空</button>
            </div>
            <div class="logs-content" ref="logsContainer">
              <div 
                v-for="(log, index) in uploadLogs" 
                :key="index"
                class="log-item"
                :class="log.type"
              >
                <span class="log-time">{{ log.time }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <!-- 取消按钮 -->
          <button 
            v-if="uploadState.stage === 'uploading' || uploadState.stage === 'processing'"
            @click="cancelUpload"
            class="btn btn-ghost btn-cancel-upload"
          >
            取消上传
          </button>
        </div>

        <!-- 操作按钮 -->
        <div class="upload-actions" v-if="selectedZip && !uploadState.isProcessing">
          <button 
            @click="uploadZipToStorage"
            :disabled="!selectedZip"
            class="btn btn-primary btn-upload"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            开始上传
          </button>
          <button @click="selectedZip = null" class="btn btn-ghost btn-cancel">
            重新选择
          </button>
        </div>
      </div>

      <!-- 训练配置 -->
      <div class="glass-card config-section" v-if="datasetStatus.valid">
        <div class="card-header">
          <div class="icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </div>
          <h3>训练配置</h3>
        </div>
        
        <!-- 基础配置 -->
        <div class="config-section-title">
          <span class="section-icon">⚙️</span>
          基础配置
        </div>
        <div class="config-grid">
          <div class="form-group">
            <label>
              <span class="label-icon">🔄</span>
              训练轮数 (Epochs)
            </label>
            <div class="input-wrapper">
              <input type="number" v-model.number="config.epochs" min="50" max="300" class="input-field">
              <span class="input-hint">{{ config.epochs < 100 ? '快速训练' : config.epochs > 200 ? '深度训练' : '标准训练' }}</span>
            </div>
            <small>数据量较少建议100轮，数据充足建议200轮</small>
          </div>

          <div class="form-group">
            <label>
              <span class="label-icon">📦</span>
              批次大小 (Batch)
            </label>
            <div class="select-wrapper">
              <select v-model.number="config.batch" class="input-field">
                <option :value="8">8 (小显存 < 4GB)</option>
                <option :value="16">16 (推荐 6-8GB)</option>
                <option :value="32">32 (大显存 > 10GB)</option>
              </select>
            </div>
          </div>

          <div class="form-group full-width">
            <label>
              <span class="label-icon">🧠</span>
              模型大小
            </label>
            <div class="model-size-options">
              <label 
                v-for="size in modelSizes" 
                :key="size.value"
                :class="['size-option', { active: config.model_size === size.value }]"
              >
                <input type="radio" v-model="config.model_size" :value="size.value">
                <span class="size-badge">{{ size.label }}</span>
                <span class="size-desc">{{ size.desc }}</span>
              </label>
            </div>
          </div>

          <div class="form-group checkbox-group">
            <label class="toggle-label">
              <div class="toggle-switch">
                <input type="checkbox" v-model="config.augmentation">
                <span class="toggle-slider"></span>
              </div>
              <div class="toggle-text">
                <span class="toggle-title">数据增强</span>
                <span class="toggle-desc">自动扩充训练数据，提升模型泛化能力</span>
              </div>
            </label>
          </div>

          <div class="form-group checkbox-group">
            <label class="toggle-label">
              <div class="toggle-switch">
                <input type="checkbox" v-model="config.incremental">
                <span class="toggle-slider"></span>
              </div>
              <div class="toggle-text">
                <span class="toggle-title">增量训练</span>
                <span class="toggle-desc">基于上次训练结果继续优化</span>
              </div>
            </label>
          </div>
        </div>

        <!-- 高级配置折叠面板 -->
        <div class="advanced-config">
          <div class="advanced-header" @click="showAdvanced = !showAdvanced">
            <div class="advanced-title">
              <span class="section-icon">🔧</span>
              高级训练选项
              <span class="advanced-badge">推荐</span>
            </div>
            <svg :class="['advanced-arrow', { open: showAdvanced }]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          
          <div v-show="showAdvanced" class="advanced-content">
            <div class="config-grid">
              <!-- 优化器设置 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">⚡</span>
                  优化器
                </label>
                <div class="select-wrapper">
                  <select v-model="config.optimizer" class="input-field">
                    <option value="AdamW">AdamW (推荐)</option>
                    <option value="Adam">Adam</option>
                    <option value="SGD">SGD (带动量)</option>
                  </select>
                </div>
                <small>AdamW 结合 Adam 和权重衰减，通常效果最好</small>
              </div>

              <!-- 学习率 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">📊</span>
                  初始学习率 (LR0)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.lr0" step="0.0001" min="0.0001" max="0.01" class="input-field">
                </div>
                <small>默认 0.001，数据少可降至 0.0005</small>
              </div>

              <!-- 图片尺寸 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">🖼️</span>
                  输入图片尺寸
                </label>
                <div class="select-wrapper">
                  <select v-model.number="config.imgsz" class="input-field">
                    <option :value="640">640 (标准)</option>
                    <option :value="800">800 (高精度)</option>
                    <option :value="1024">1024 (超高精度)</option>
                  </select>
                </div>
                <small>大尺寸提升小目标检测，但训练更慢</small>
              </div>

              <!-- 早停耐心值 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">⏱️</span>
                  早停耐心 (Patience)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.patience" min="10" max="50" class="input-field">
                </div>
                <small>连续多少轮无提升则停止，默认 20</small>
              </div>

              <!-- 权重衰减 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">🎯</span>
                  权重衰减 (Weight Decay)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.weight_decay" step="0.0001" min="0" max="0.001" class="input-field">
                </div>
                <small>防止过拟合，默认 0.0005</small>
              </div>

              <!-- Dropout -->
              <div class="form-group">
                <label>
                  <span class="label-icon">💧</span>
                  Dropout 率
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.dropout" step="0.05" min="0" max="0.5" class="input-field">
                </div>
                <small>随机丢弃神经元比例，防止过拟合</small>
              </div>

              <!-- 标签平滑 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">🏷️</span>
                  标签平滑 (Label Smoothing)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.label_smoothing" step="0.01" min="0" max="0.1" class="input-field">
                </div>
                <small>软化标签，提升泛化能力，默认 0.0</small>
              </div>

              <!-- 冻结层数 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">🧊</span>
                  冻结层数 (Freeze)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.freeze" min="0" max="24" class="input-field">
                </div>
                <small>冻结主干网络层数，0 表示全部可训练</small>
              </div>

              <!-- 预热轮数 -->
              <div class="form-group">
                <label>
                  <span class="label-icon">🔥</span>
                  预热轮数 (Warmup)
                </label>
                <div class="input-wrapper">
                  <input type="number" v-model.number="config.warmup_epochs" min="0" max="10" class="input-field">
                </div>
                <small>学习率从低到高预热，默认 3 轮</small>
              </div>
            </div>

            <!-- 数据增强高级选项 -->
            <div class="augmentation-section" v-if="config.augmentation">
              <div class="subsection-title">🎨 数据增强强度</div>
              <div class="config-grid">
                <div class="form-group">
                  <label>Mosaic 混合</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.mosaic" min="0" max="1" step="0.1" class="slider">
                    <span class="slider-value">{{ config.mosaic }}</span>
                  </div>
                </div>

                <div class="form-group">
                  <label>MixUp 混合</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.mixup" min="0" max="1" step="0.1" class="slider">
                    <span class="slider-value">{{ config.mixup }}</span>
                  </div>
                </div>

                <div class="form-group">
                  <label>Copy-Paste 复制粘贴</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.copy_paste" min="0" max="1" step="0.1" class="slider">
                    <span class="slider-value">{{ config.copy_paste }}</span>
                  </div>
                </div>

                <div class="form-group">
                  <label>旋转角度 (Degrees)</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.degrees" min="0" max="45" step="1" class="slider">
                    <span class="slider-value">{{ config.degrees }}°</span>
                  </div>
                </div>

                <div class="form-group">
                  <label>缩放范围 (Scale)</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.scale" min="0" max="1" step="0.1" class="slider">
                    <span class="slider-value">{{ config.scale }}</span>
                  </div>
                </div>

                <div class="form-group">
                  <label>剪切变换 (Shear)</label>
                  <div class="slider-wrapper">
                    <input type="range" v-model.number="config.shear" min="0" max="20" step="1" class="slider">
                    <span class="slider-value">{{ config.shear }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 预设配置 -->
            <div class="preset-section">
              <div class="subsection-title">⚡ 快速预设</div>
              <div class="preset-buttons">
                <button @click="applyPreset('fast')" class="btn btn-preset preset-fast">
                  🚀 快速训练
                  <span>适合快速验证</span>
                </button>
                <button @click="applyPreset('balanced')" class="btn btn-preset preset-balanced">
                  ⚖️ 平衡模式
                  <span>推荐大多数场景</span>
                </button>
                <button @click="applyPreset('accuracy')" class="btn btn-preset preset-accuracy">
                  🎯 高精度模式
                  <span>追求最佳 mAP</span>
                </button>
                <button @click="applyPreset('kaggle')" class="btn btn-preset preset-kaggle">
                  🔥 Kaggle 竞赛
                  <span>突破 0.63 配置</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <button 
          @click="prepareAndStartTraining" 
          :disabled="!datasetStatus.valid || trainingLoading || downloadProgress.show"
          class="btn btn-primary btn-large"
        >
          <svg v-if="trainingLoading" class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          <svg v-else-if="downloadProgress.show" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          {{ trainingLoading ? '启动训练引擎...' : downloadProgress.show ? '等待下载完成...' : '开始训练模型' }}
        </button>

        <div v-if="trainingMessage" :class="['message-toast', trainingMessage.type]">
          <div class="toast-icon">
            <svg v-if="trainingMessage.type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </div>
          <span>{{ trainingMessage.text }}</span>
        </div>
      </div>

      <!-- 上传提示 -->
      <div v-if="trainingStatus.pending_upload && trainingStatus.latest_model" class="glass-card upload-prompt">
        <div class="upload-header">
          <div class="success-icon">🎉</div>
          <div class="upload-title">
            <h4>训练完成</h4>
            <p>模型已就绪，可上传至云端保存</p>
          </div>
        </div>
        
        <div class="model-preview">
          <div class="preview-item">
            <span class="preview-label">版本</span>
            <span class="preview-value">{{ trainingStatus.latest_model.version_name || '未知' }}</span>
          </div>
          <div class="preview-item">
            <span class="preview-label">精度 (mAP50)</span>
            <span class="preview-value highlight">{{ formatMetric(trainingStatus.latest_model.metrics && trainingStatus.latest_model.metrics.map50) }}</span>
          </div>
        </div>
        
        <div class="upload-actions">
          <button @click="uploadToCloud" :disabled="uploading" class="btn btn-primary">
            <svg v-if="uploading" class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            {{ uploading ? '上传中...' : '上传至云端' }}
          </button>
          <button @click="skipUpload" class="btn btn-ghost">
            稍后处理
          </button>
        </div>
      </div>

      <!-- 模型库 -->
      <div class="glass-card models-section">
        <div class="card-header">
          <div class="icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
              <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
          </div>
          <h3>模型库</h3>
          <span class="model-count">{{ models.length }} 个模型</span>
        </div>
        
        <div v-if="models.length === 0" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无模型</p>
          <span>完成训练后，模型将显示在这里</span>
        </div>
        
        <div v-else class="models-list">
          <div 
            v-for="model in models" 
            :key="model.name || model.version_name"
            :class="['model-item', { active: (model.name || model.version_name) === currentModel }]"
          >
            <div class="model-main">
              <div class="model-avatar">
                {{ (model.displayName || model.name || '?').charAt(0).toUpperCase() }}
              </div>
              <div class="model-info">
                <span class="model-name">{{ model.displayName || model.name }}</span>
                <div class="model-meta">
                  <span v-if="model.map50" class="model-score">
                    <span class="score-icon">🎯</span>
                    {{ (model.map50 * 100).toFixed(1) }}%
                  </span>
                  <span :class="['cloud-badge', model.model_path || model.cloud_path ? 'uploaded' : 'local']">
                    {{ model.model_path || model.cloud_path ? '☁️ 云端' : '💻 本地' }}
                  </span>
                </div>
              </div>
            </div>
            
            <div class="model-actions">
              <button 
                v-if="(model.name || model.version_name) !== currentModel"
                @click="switchModel(model)"
                class="btn btn-small btn-success"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
                激活
              </button>
              <span v-else class="current-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                使用中
              </span>
              
              <button 
                v-if="!model.model_path && !model.cloud_path"
                @click="uploadModel(model)"
                :disabled="uploadingModel === (model.name || model.version_name)"
                class="btn btn-small btn-primary"
              >
                <svg v-if="uploadingModel === (model.name || model.version_name)" class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                {{ uploadingModel === (model.name || model.version_name) ? '上传中' : '上传' }}
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { createClient } from '@supabase/supabase-js'
import { ref, reactive, nextTick, onMounted, onUnmounted, computed } from 'vue'
import GradientBackground from '@/components/GradientBackground.vue'

const route = useRoute()

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)

const API_BASE = 'http://localhost:8000/api'

// ===== 数据集分页状态 =====  ← 新增
const datasetPage = ref(0)
const datasetLimit = ref(20)
const datasetSearch = ref('')
const datasetTotal = ref(0)
const datasetHasMore = ref(false)
// ===== 数据集管理 =====
const availableDatasets = ref([])
const selectedDatasetId = ref('')
const selectedDataset = computed(() => 
  availableDatasets.value.find(d => d.id === selectedDatasetId.value)
)

const fetchDatasets = async (append = false) => {
  try {
    const params = new URLSearchParams({
      limit: String(datasetLimit.value),
      offset: String(datasetPage.value * datasetLimit.value)
    })
    if (datasetSearch.value) {
      params.append('search', datasetSearch.value)
    }
    
    const res = await fetch(`${API_BASE}/datasets?${params}`)
    const data = await res.json()
    
    if (data.datasets) {
      const datasetsWithStatus = data.datasets.map((ds) => {
  const datasetId = ds.id || ds.dataset_id || 'default'

  return {
    ...ds,
    id: datasetId,
    cached: ds.cached || false,
    stats: ds.stats || {},
    is_active: ds.is_active || datasetId === data.active_dataset_id
  }
})
      
      if (append) {
        const existingIds = new Set(availableDatasets.value.map(d => d.id))
        const newItems = datasetsWithStatus.filter(d => !existingIds.has(d.id))
        availableDatasets.value.push(...newItems)
      } else {
        availableDatasets.value = datasetsWithStatus
      }
      
      datasetTotal.value = data.total || 0
      datasetHasMore.value = data.has_more || false
      
      if (!selectedDatasetId.value || selectedDatasetId.value === 'undefined') {
        if (data.active_dataset_id && data.active_dataset_id !== 'undefined') {
          selectedDatasetId.value = data.active_dataset_id
        } else {
          const defaultDs = datasetsWithStatus.find(d => d.id === 'default' || d.is_base)
          if (defaultDs) {
            selectedDatasetId.value = defaultDs.id
          } else if (datasetsWithStatus.length > 0) {
            selectedDatasetId.value = datasetsWithStatus[0].id
          }
        }
      }
    }
  } catch (e) {
    console.error('获取数据集列表失败:', e)
  }
}

const loadMoreDatasets = async () => {
  if (!datasetHasMore.value) return
  datasetPage.value += 1
  await fetchDatasets(true)
}

const searchDatasets = async () => {
  datasetPage.value = 0
  await fetchDatasets(false)
}
const selectDataset = async (datasetId) => {
  if (!datasetId || datasetId === 'undefined' || datasetId === 'null') {
    console.warn(`无效的 datasetId: ${datasetId}，回退到 default`)
    datasetId = 'default'
  }
  
  // 先重置选中状态，如果失败再恢复
  const previousDatasetId = selectedDatasetId.value
  selectedDatasetId.value = datasetId
  
  try {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/switch`, {
      method: 'POST'
    })
    const data = await res.json()
    
    // 关键修复：判断 HTTP 状态码
    if (!res.ok) {
      // 恢复之前的选择
      selectedDatasetId.value = previousDatasetId
      
      const errorMsg = data.detail || data.message || `切换失败 (HTTP ${res.status})`
      console.error('切换数据集失败:', errorMsg)
      
      // 显示错误提示 - 使用全局错误显示
      showGlobalError(`切换数据集失败: ${errorMsg}`)
      return
    }
    
    if (data.success) {
      const idx = availableDatasets.value.findIndex(d => d.id === datasetId)
      if (idx >= 0) {
        availableDatasets.value[idx].cached = true
        availableDatasets.value[idx].stats = data.stats || {}
      }
      // 传递错误处理器，确保 checkDataset 的错误也能被捕获
      const checkResult = await checkDataset({
        onError: (err) => showGlobalError(`数据集状态检查失败: ${err}`)
      })
      if (!checkResult.success) {
        // checkDataset 已经显示了错误，这里只需要确保数据集状态正确
        datasetStatus.value.valid = false
      }
    } else {
      throw new Error(data.message || '切换数据集失败')
    }
  } catch (e) {
    // 恢复之前的选择
    selectedDatasetId.value = previousDatasetId
    
    console.error('切换数据集失败:', e)
    showGlobalError(`切换数据集失败: ${e.message}`)
  }
}

// 新增：全局错误显示函数
const globalError = ref(null)
let errorTimer = null

const showGlobalError = (message) => {
  // 清除之前的定时器
  if (errorTimer) clearTimeout(errorTimer)
  
  globalError.value = message
  
  // 5秒后自动清除
  errorTimer = setTimeout(() => {
    globalError.value = null
  }, 5000)
}

const clearGlobalError = () => {
  globalError.value = null
  if (errorTimer) clearTimeout(errorTimer)
}

// ===== 状态管理 =====
const selectedZip = ref(null)
const isDragging = ref(false)
const logsContainer = ref(null)
const uploading = ref(false)

const uploadState = reactive({
  isProcessing: false,
  stage: '',
  title: '',
  message: '',
  percent: 0,
  cancelToken: null
})

const uploadSteps = reactive([
  { name: '选择文件', desc: '验证 ZIP 格式', status: 'pending', detail: '' },
  { name: '上传云端', desc: '上传到 Supabase Storage', status: 'pending', detail: '' },
  { name: '解压处理', desc: '解析数据集结构', status: 'pending', detail: '' },
  { name: '数据验证', desc: '检查 images/ 和 labels/', status: 'pending', detail: '' },
  { name: '重新打包', desc: '生成标准 YOLO 格式', status: 'pending', detail: '' },
  { name: '保存记录', desc: '写入数据库', status: 'pending', detail: '' }
])

const uploadLogs = reactive([])

const datasetStatus = ref({
  valid: false,
  message: '检查数据集状态...',
  details: null
})

const cacheStatus = ref({
  cached: false,
  cache_path: null
})

const downloadProgress = reactive({
  show: false,
  percent: 0,
  message: '',
  detail: '',
  status: '',
  dataset_id: ''
})

const downloadSteps = reactive([
  { name: '获取文件信息', completed: false, active: false },
  { name: '下载数据集', completed: false, active: false },
  { name: '解压文件', completed: false, active: false },
  { name: '验证结构', completed: false, active: false },
  { name: '生成配置', completed: false, active: false }
])

const hardwareInfo = ref({
  cuda_available: false,
  cuda_device: null
})

const checking = ref(false)
const trainingLoading = ref(false)
const trainingMessage = ref(null)

const models = ref([])
const currentModel = ref('')
const uploadingModel = ref('')
const showAdvanced = ref(false)

const trainingStatus = ref({
  pending_upload: false,
  latest_model: null
})

const config = ref({
  epochs: 100,
  batch: 16,
  model_size: 'auto',
  augmentation: true,
  incremental: false,
  optimizer: 'AdamW',
  lr0: 0.001,
  imgsz: 640,
  patience: 20,
  weight_decay: 0.0005,
  dropout: 0.0,
  label_smoothing: 0.0,
  freeze: 0,
  warmup_epochs: 3,
  mosaic: 1.0,
  mixup: 0.1,
  copy_paste: 0.0,
  degrees: 15,
  scale: 0.5,
  shear: 5
})

let wsConnection = null
let progressPollInterval = null

// ===== 工具函数 =====
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const addLog = (message, type = 'info') => {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`
  uploadLogs.push({ time, message, type })
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  })
}

const updateStep = (index, status, detail = '') => {
  uploadSteps[index].status = status
  if (detail) uploadSteps[index].detail = detail
}

const resetUploadState = () => {
  uploadState.isProcessing = false
  uploadState.stage = ''
  uploadState.title = ''
  uploadState.message = ''
  uploadState.percent = 0
  uploadState.cancelToken = null
  uploadSteps.forEach(step => {
    step.status = 'pending'
    step.detail = ''
  })
  uploadLogs.splice(0, uploadLogs.length)
}

const handleZipSelect = (event) => {
  const file = event.target.files[0]
  validateAndSetZip(file)
}

const handleZipDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  validateAndSetZip(file)
}

const validateAndSetZip = (file) => {
  if (!file) return
  if (!file.name.endsWith('.zip')) {
    alert('请选择 ZIP 格式的文件')
    return
  }
  if (file.size > 2 * 1024 * 1024 * 1024) {
    alert('文件大小超过 2GB 限制')
    return
  }
  selectedZip.value = file
  addLog(`已选择文件: ${file.name} (${formatFileSize(file.size)})`)
}

const uploadZipToStorage = async () => {
  if (!selectedZip.value) return

  resetUploadState()
  uploadState.isProcessing = true
  uploadState.stage = 'uploading'
  uploadState.title = '正在上传'
  uploadState.message = '准备上传...'
  updateStep(0, 'completed', selectedZip.value.name)
  updateStep(1, 'active')

  try {
    const datasetId = selectedDatasetId.value || 'default'
    const timestamp = new Date().toISOString().slice(0,19).replace(/[:T]/g, '-')
    const uploadDatasetId = `${datasetId}_local_${timestamp}`
    const storagePath = `projects/${uploadDatasetId}.zip`

    addLog(`开始上传: ${storagePath}`)

    const abortController = new AbortController()
    uploadState.cancelToken = abortController

    const { data: uploadData, error: uploadError } = await supabase.storage
      .from('datasets')
      .upload(storagePath, selectedZip.value, {
        cacheControl: '3600',
        upsert: false,
        onUploadProgress: (progress) => {
          const percent = Math.round((progress.loaded / progress.total) * 40)
          uploadState.percent = percent
          uploadState.message = `已上传 ${formatFileSize(progress.loaded)} / ${formatFileSize(progress.total)}`
          uploadSteps[1].detail = `${percent}% (${formatFileSize(progress.loaded)})`
          addLog(`上传进度: ${percent}%`, 'info')
        }
      })

    if (uploadError) throw uploadError

    addLog('Storage 上传成功', 'success')
    updateStep(1, 'completed')
    updateStep(2, 'active')
    
    uploadState.stage = 'processing'
    uploadState.title = '服务器处理中'
    uploadState.message = '正在解析数据集...'
    uploadState.percent = 45

    addLog('开始后端处理...')

    const response = await fetch('/api/dataset/process-from-storage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_name: uploadDatasetId,
        storage_path: storagePath,
        bucket: 'datasets',
        original_filename: selectedZip.value.name,
        file_size: selectedZip.value.size
      }),
      signal: abortController.signal
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || `HTTP ${response.status}`)
    }

    const result = await response.json()
    await simulateProcessingProgress()

    uploadState.stage = 'completed'
    uploadState.title = '上传成功'
    uploadState.message = `数据集包含 ${result.stats?.total || 0} 张图片`
    uploadState.percent = 100
    
    updateStep(2, 'completed')
    updateStep(3, 'completed')
    updateStep(4, 'completed')
    updateStep(5, 'completed', `ID: ${result.dataset_id}`)

    addLog(`处理完成: ${result.message}`, 'success')

    setTimeout(async () => {
      await fetchDatasets()
      await checkDataset()
      selectedZip.value = null
      resetUploadState()
    }, 2000)

  } catch (e) {
    if (e.name === 'AbortError') {
      uploadState.title = '已取消'
      uploadState.message = '上传已取消'
      addLog('用户取消上传', 'warning')
    } else {
      uploadState.stage = 'error'
      uploadState.title = '上传失败'
      uploadState.message = e.message
      addLog(`错误: ${e.message}`, 'error')
      const currentStep = uploadSteps.findIndex(s => s.status === 'active')
      if (currentStep >= 0) updateStep(currentStep, 'error')
    }
  }
}

const simulateProcessingProgress = async () => {
  const steps = [
    { percent: 50, message: '解压 ZIP 文件...', stepIndex: 2 },
    { percent: 60, message: '分析数据集结构...', stepIndex: 2 },
    { percent: 70, message: '验证图片和标签...', stepIndex: 3 },
    { percent: 80, message: '重新打包数据集...', stepIndex: 4 },
    { percent: 90, message: '保存到数据库...', stepIndex: 5 },
    { percent: 95, message: '清理临时文件...', stepIndex: 5 }
  ]

  for (const step of steps) {
    await new Promise(r => setTimeout(r, 500))
    uploadState.percent = step.percent
    uploadState.message = step.message
    if (step.stepIndex >= 0) {
      updateStep(step.stepIndex, 'completed')
      if (step.stepIndex + 1 < uploadSteps.length) {
        updateStep(step.stepIndex + 1, 'active')
      }
    }
    addLog(step.message)
  }
}

const cancelUpload = () => {
  if (uploadState.cancelToken) {
    uploadState.cancelToken.abort()
  }
}

// ===== 修复：数据集状态检查 - 使用 datasetId 替代 projectId =====
const checkDataset = async (options = {}) => {
  const { onError } = options
  checking.value = true
  try {
    let datasetId = selectedDatasetId.value
    if (!datasetId || datasetId === 'undefined' || datasetId === 'null' || datasetId === '') {
      datasetId = 'default'
      selectedDatasetId.value = 'default'
    }
    
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/status`)
    const data = await res.json()
    
    // 处理后端返回的错误
    if (!res.ok) {
      const errorMsg = data.detail || data.message || '检查数据集状态失败'
      datasetStatus.value = {
        valid: false,
        message: errorMsg
      }
      console.error('检查数据集状态失败:', errorMsg)
      // 如果有外部错误处理器，调用它
      if (onError) onError(errorMsg)
      return { success: false, error: errorMsg }
    }
    
    const isValid = data.cached || data.exists || (data.stats && (data.stats.total > 0 || data.stats.train > 0))
    
    datasetStatus.value = {
      valid: isValid,
      message: data.cached 
        ? `数据集已就绪: ${data.dataset_name || datasetId}` 
        : data.exists || (data.stats && data.stats.total > 0)
          ? `数据集存在于云端 (${data.stats?.total || 0} 张图片)，训练时将自动下载` 
          : '数据集未找到',
      details: {
        stats: data.stats || {},
        dataset_id: data.dataset_id || datasetId,
        storage_path: data.cache_path || data.storage_path
      }
    }
    
    cacheStatus.value = {
      cached: data.cached || false,
      cache_path: data.cache_path || data.storage_path
    }
    
    // 获取硬件信息和模型列表
    try {
      const hwRes = await fetch(`${API_BASE}/training/status`)
      const hwData = await hwRes.json()
      hardwareInfo.value = {
        cuda_available: hwData.cuda_available,
        cuda_device: hwData.cuda_device
      }
      
      const allModels = [
        ...(hwData.local_models || []).map(m => ({
          name: m.name,
          displayName: m.name,
          path: m.path,
          local_path: m.path,
          model_path: null,
          map50: null,
          is_active: m.is_active,
          modified: m.modified
        })),
        ...(hwData.cloud_models || []).map(m => ({
          name: m.version_name || m.name,
          displayName: m.version_name || m.name,
          path: m.local_path,
          local_path: m.local_path,
          model_path: m.model_path,
          map50: m.map50 || m.metrics?.map50,
          is_active: m.is_active,
          modified: m.created_at
        }))
      ]
      
      const modelMap = new Map()
      for (const model of allModels) {
        const key = model.name
        if (!modelMap.has(key) || model.model_path) {
          modelMap.set(key, model)
        }
      }
      models.value = Array.from(modelMap.values())
      currentModel.value = hwData.current_model || ''
      
      if (hwData.pending_upload && hwData.latest_model) {
        trainingStatus.value = {
          pending_upload: true,
          latest_model: hwData.latest_model
        }
      } else {
        trainingStatus.value = {
          pending_upload: false,
          latest_model: null
        }
      }
    } catch (hwErr) {
      console.error('获取硬件信息失败:', hwErr)
    }
    
    return { success: true, data }
    
  } catch (e) {
    console.error('检查数据集状态失败:', e)
    const errorMsg = '检查失败: ' + e.message
    datasetStatus.value = {
      valid: false,
      message: errorMsg
    }
    if (onError) onError(errorMsg)
    return { success: false, error: errorMsg }
  } finally {
    checking.value = false
  }
}
const connectWebSocket = () => {
  const token = localStorage.getItem('token') || ''
  const wsUrl = `ws://localhost:8000/api/ws/progress?token=${token}`
  
  wsConnection = new WebSocket(wsUrl)
  
  wsConnection.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'DATASET_DOWNLOAD_PROGRESS') {
        downloadProgress.percent = data.percent
        downloadProgress.message = data.message
        downloadProgress.detail = data.detail || ''
        downloadProgress.status = data.status || 'downloading'
        downloadProgress.dataset_id = data.dataset_id
        updateDownloadSteps(data.percent)
        
        if (data.status === 'completed') {
          downloadProgress.show = false
          cacheStatus.value.cached = true
          startTraining()
        }
        if (data.status === 'error') {
          trainingMessage.value = {
            type: 'error',
            text: '数据集下载失败: ' + (data.detail || '未知错误')
          }
          downloadProgress.show = false
          trainingLoading.value = false
        }
      }
    } catch (e) {
      console.error('WebSocket 消息解析失败:', e)
    }
  }
  
  wsConnection.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }
  
  wsConnection.onclose = () => {
    setTimeout(() => {
      if (!wsConnection || wsConnection.readyState === WebSocket.CLOSED) {
        connectWebSocket()
      }
    }, 5000)
  }
}

const updateDownloadSteps = (percent) => {
  const stepIndex = Math.floor(percent / 20)
  downloadSteps.forEach((step, index) => {
    step.completed = index < stepIndex
    step.active = index === stepIndex
  })
}

const prepareAndStartTraining = async () => {
  trainingLoading.value = true
  trainingMessage.value = null
  
  try {
        let datasetId = selectedDatasetId.value
    if (!datasetId || datasetId === 'undefined' || datasetId === 'null' || datasetId === '') {
      datasetId = 'default'
      selectedDatasetId.value = 'default'
    }
    if (!datasetId) {
      throw new Error('请先选择一个数据集')
    }
    
    if (cacheStatus.value.cached) {
      await startTraining()
      return
    }
    
    downloadProgress.show = true
    downloadProgress.status = 'downloading'
    downloadProgress.percent = 0
    downloadProgress.message = '准备下载...'
    
    downloadSteps.forEach(step => {
      step.completed = false
      step.active = false
    })
    
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/prepare`, {
      method: 'POST'
    })
    
    const data = await res.json()
    
    if (!data.success) {
      throw new Error(data.message || '准备训练失败')
    }
    
    if (data.cached) {
      downloadProgress.show = false
      cacheStatus.value.cached = true
      await startTraining()
      return
    }
    
    startProgressPolling(datasetId)
    
  } catch (e) {
    trainingLoading.value = false
    downloadProgress.show = false
    trainingMessage.value = {
      type: 'error',
      text: '启动失败: ' + e.message
    }
  }
}

const startProgressPolling = (datasetId) => {
  if (progressPollInterval) {
    clearInterval(progressPollInterval)
  }
  
  progressPollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/status`)
      const data = await res.json()
      
      if (data.cached) {
        clearInterval(progressPollInterval)
        progressPollInterval = null
        downloadProgress.show = false
        cacheStatus.value.cached = true
        await startTraining()
        return
      }
      
      downloadProgress.percent = Math.min(downloadProgress.percent + 5, 95)
      downloadProgress.message = '正在下载数据集...'
      
    } catch (e) {
      console.error('轮询进度失败:', e)
    }
  }, 1000)
}

const startTraining = async () => {
  try {
      let datasetId = selectedDatasetId.value
    if (!datasetId || datasetId === 'undefined' || datasetId === 'null' || datasetId === '') {
      datasetId = 'default'
      selectedDatasetId.value = 'default'
    }
    
    const params = new URLSearchParams({
      dataset_id: datasetId,
      epochs: config.value.epochs,
      batch: config.value.batch,
      model_size: config.value.model_size,
      augmentation: config.value.augmentation,
      optimizer: config.value.optimizer,
      lr0: config.value.lr0,
      imgsz: config.value.imgsz,
      patience: config.value.patience,
      weight_decay: config.value.weight_decay,
      dropout: config.value.dropout,
      label_smoothing: config.value.label_smoothing,
      freeze: config.value.freeze,
      warmup_epochs: config.value.warmup_epochs,
      mosaic: config.value.mosaic,
      mixup: config.value.mixup,
      copy_paste: config.value.copy_paste,
      degrees: config.value.degrees,
      scale: config.value.scale,
      shear: config.value.shear
    })
    
    const res = await fetch(`${API_BASE}/training/start?${params}`, {
      method: 'POST'
    })
    const data = await res.json()
    
    if (data.success) {
      trainingMessage.value = {
        type: 'success',
        text: `训练已启动！模型: ${data.config.model_size}, 轮数: ${data.config.epochs}`
      }
      startPolling()
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

const presets = {
  fast: {
    epochs: 50, batch: 16, imgsz: 640, patience: 10, lr0: 0.001,
    optimizer: 'AdamW', freeze: 10, dropout: 0, augmentation: true,
    mosaic: 0.5, mixup: 0, degrees: 5, scale: 0.3
  },
  balanced: {
    epochs: 100, batch: 16, imgsz: 640, patience: 20, lr0: 0.001,
    optimizer: 'AdamW', freeze: 0, dropout: 0.05, augmentation: true,
    mosaic: 1.0, mixup: 0.1, degrees: 15, scale: 0.5
  },
  accuracy: {
    epochs: 200, batch: 8, imgsz: 800, patience: 30, lr0: 0.0005,
    optimizer: 'AdamW', freeze: 0, dropout: 0.1, label_smoothing: 0.05,
    augmentation: true, mosaic: 1.0, mixup: 0.3, copy_paste: 0.2,
    degrees: 20, scale: 0.6, shear: 8
  },
  kaggle: {
    epochs: 80, batch: 6, imgsz: 800, patience: 20, lr0: 0.001,
    optimizer: 'AdamW', freeze: 0, dropout: 0.1, weight_decay: 0.0005,
    label_smoothing: 0.05, augmentation: true, mosaic: 1.0, mixup: 0.3,
    copy_paste: 0.4, degrees: 15, scale: 0.6, shear: 5, warmup_epochs: 5
  }
}

const applyPreset = (presetName) => {
  const preset = presets[presetName]
  if (preset) {
    Object.assign(config.value, preset)
    if (preset.augmentation !== undefined) {
      config.value.augmentation = preset.augmentation
    }
  }
}

const modelSizes = [
  { value: 'auto', label: 'Auto', desc: '智能选择最佳模型' },
  { value: 'n', label: 'Nano', desc: '极速训练，低精度' },
  { value: 's', label: 'Small', desc: '快速训练，中等精度' },
  { value: 'm', label: 'Medium', desc: '平衡速度与精度' },
  { value: 'l', label: 'Large', desc: '高精度，较慢' },
  { value: 'x', label: 'XLarge', desc: '最高精度，最慢' }
]

const formatMetric = (value) => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

const uploadToCloud = async () => {
  uploading.value = true
  try {
    const res = await fetch(`${API_BASE}/models/upload`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      alert('✅ ' + data.message)
      checkDataset()
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    alert('❌ 上传失败: ' + e.message)
  } finally {
    uploading.value = false
  }
}

const skipUpload = async () => {
  try {
    await fetch(`${API_BASE}/models/skip-upload`, { method: 'POST' })
    checkDataset()
  } catch (e) {
    console.error(e)
  }
}

const switchModel = async (model) => {
  const modelName = model.name || model.version_name
  
  try {
    if (model.is_active || modelName === currentModel.value) return
    
    const path = model.path || model.local_path
    if (!path) {
      alert('模型路径不存在')
      return
    }
    
    const previousModel = currentModel.value
    currentModel.value = modelName
    
    models.value = models.value.map(m => {
      const mName = m.name || m.version_name
      return { ...m, is_active: mName === modelName }
    })
    
    const res = await fetch(`${API_BASE}/models/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, name: modelName })
    })
    
    const data = await res.json()
    
    if (!data.success) {
      currentModel.value = previousModel
      models.value = models.value.map(m => ({
        ...m,
        is_active: (m.name || m.version_name) === previousModel
      }))
      throw new Error(data.message || '切换失败')
    }
  } catch (e) {
    alert('切换失败: ' + e.message)
  }
}

const uploadModel = async (model) => {
  const modelName = model.name || model.version_name
  uploadingModel.value = modelName
  
  try {
    const encodedName = encodeURIComponent(modelName)
    
    const res = await fetch(`${API_BASE}/models/${encodedName}/upload`, {
      method: 'POST'
    })
    
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP ${res.status}`)
    }
    
    const data = await res.json()
    
    if (data.success) {
      alert(`✅ ${data.message}\n大小: ${data.size_mb} MB`)
      checkDataset()
    } else {
      throw new Error(data.message || '上传失败')
    }
  } catch (e) {
    alert('❌ 上传失败: ' + e.message)
  } finally {
    uploadingModel.value = ''
  }
}

let pollInterval = null
const startPolling = () => {
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

onMounted(() => {
  fetchDatasets().then(() => {
    checkDataset()
  })
  connectWebSocket()
})

onUnmounted(() => {
  if (wsConnection) {
    wsConnection.close()
  }
  if (progressPollInterval) {
    clearInterval(progressPollInterval)
  }
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style scoped>
/* ===== 基础变量与动画 ===== */
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse-ring {
  0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}

@keyframes shine {
  0% { left: -100%; }
  100% { left: 100%; }
}

@keyframes step-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ===== 页面布局 ===== */
.training-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f4f8 50%, #e8eef5 100%);
  position: relative;
  overflow-x: hidden;
  color: #2c3e50;
}

.bg-decoration {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.orb-2 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  bottom: 10%;
  left: -50px;
  animation: float 10s ease-in-out infinite reverse;
}

.orb-3 {
  width: 250px;
  height: 250px;
  background: linear-gradient(135deg, #10b981, #06b6d4);
  top: 40%;
  right: 10%;
  animation: float 12s ease-in-out infinite;
}

/* ===== 内容包装器 ===== */
.content-wrapper {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}

/* ===== 页面标题 ===== */
.page-header {
  text-align: center;
  margin-bottom: 40px;
  animation: slideIn 0.6s ease-out;
}

.title-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 40px rgba(99, 102, 241, 0.2);
}

.title-icon svg {
  width: 32px;
  height: 32px;
  color: white;
}

.page-header h1 {
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0 0 8px;
  color: #1e293b;
}

.subtitle {
  color: #64748b;
  font-size: 1rem;
  margin: 0;
}

/* ===== 玻璃卡片 ===== */
.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 20px;
  padding: 28px;
  margin-bottom: 16px;
  animation: slideIn 0.6s ease-out;
  transition: all 0.3s ease;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.glass-card:hover {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border-color: rgba(99, 102, 241, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.icon-wrapper {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-wrapper svg {
  width: 20px;
  height: 20px;
  color: #6366f1;
}

.card-header h3 {
  flex: 1;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

/* ===== 状态卡片 ===== */
.status-card {
  border-left: 4px solid #ef4444;
}

.status-card.ready {
  border-left-color: #10b981;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.success {
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
}

.status-badge.warning {
  background: rgba(245, 158, 11, 0.15);
  color: #d97706;
}

.status-message {
  color: #64748b;
  margin: 0 0 14px;
  font-size: 0.9rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.stat-item {
  background: rgba(241, 245, 249, 0.8);
  border-radius: 12px;
  padding: 14px;
  text-align: center;
  border: 1px solid rgba(226, 232, 240, 0.6);
  transition: all 0.3s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(241, 245, 249, 1);
}

.stat-icon {
  font-size: 1.25rem;
  margin-bottom: 6px;
}

.stat-value {
  display: block;
  font-size: 1.55rem;
  font-weight: 700;
  color: #6366f1;
  line-height: 1;
}

.stat-label {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 4px;
}

/* 缓存状态 */
.cache-info {
  margin: 16px 0;
}

.cache-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  font-size: 0.85rem;
  color: #6366f1;
}

.cache-badge.success {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
  color: #059669;
}

/* 硬件信息 */
.hardware-info {
  margin-top: 16px;
}

.gpu-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 8px;
  font-size: 0.8rem;
  color: #059669;
}

.gpu-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
  color: #d97706;
}

.gpu-icon {
  font-size: 1rem;
}

/* ===== 下载进度卡片 ===== */
.download-progress-card {
  border: 2px solid rgba(99, 102, 241, 0.3);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.03));
}

.download-progress-content {
  padding: 8px 0;
}

.download-steps {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #e2e8f0;
}

.download-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  opacity: 0.5;
  transition: all 0.3s ease;
}

.download-step.active {
  opacity: 1;
}

.download-step.completed {
  opacity: 1;
}

.download-step .step-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.3s ease;
}

.download-step.completed .step-dot {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.download-step.active .step-dot {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

.download-step .step-name {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
}

.download-step.active .step-name {
  color: #6366f1;
  font-weight: 600;
}

.download-step.completed .step-name {
  color: #059669;
}

/* ===== 上传数据集卡片 ===== */
.upload-dataset-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
  margin-top: 0;
  margin-bottom: 14px;
}

.upload-dataset-card .header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-desc {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
  font-weight: 400;
}

.upload-icon {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15)) !important;
}

.upload-icon svg {
  color: #6366f1 !important;
}

/* ===== 拖拽区域 ===== */
.drop-zone {
  position: relative;
  border: 2px dashed #cbd5e1;
  border-radius: 20px;
  padding: 48px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.8));
  overflow: hidden;
}

.drop-zone:hover, .drop-zone.dragging {
  border-color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.1);
}

.drop-zone-inner {
  position: relative;
  z-index: 1;
}

.drop-illustration {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.upload-circle {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
  position: relative;
  z-index: 2;
}

.upload-circle svg {
  width: 32px;
  height: 32px;
  color: white;
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  border: 2px solid rgba(99, 102, 241, 0.3);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
  z-index: 1;
}

.drop-text {
  margin-bottom: 16px;
}

.drop-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px;
}

.drop-subtitle {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0;
}

.drop-format {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.format-tag {
  padding: 4px 12px;
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.format-divider {
  color: #cbd5e1;
}

/* ===== ZIP 信息 ===== */
.zip-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
  border-radius: 12px;
  margin-top: 20px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.zip-icon {
  font-size: 2rem;
}

.zip-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zip-name {
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}

.zip-size {
  font-size: 0.85rem;
  color: #64748b;
}

.zip-remove {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.zip-remove:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* ===== 进度面板 ===== */
.progress-panel {
  margin-top: 24px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.9));
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.progress-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.progress-icon.uploading {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
}

.progress-icon.processing {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.15));
}

.progress-icon.completed {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
}

.progress-icon.error {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.15));
}

.progress-title-group {
  flex: 1;
}

.progress-title {
  margin: 0 0 4px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.progress-subtitle {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}

.progress-percentage {
  font-size: 1.5rem;
  font-weight: 700;
  color: #6366f1;
}

/* ===== 进度条 ===== */
.progress-bar-container {
  margin-bottom: 24px;
}

.progress-track {
  height: 10px;
  background: #e2e8f0;
  border-radius: 5px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.progress-fill.uploading, .progress-fill.downloading {
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
}

.progress-fill.processing {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.progress-fill.completed {
  background: linear-gradient(90deg, #10b981, #059669);
}

.progress-fill.error {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.progress-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  animation: shine 1.5s infinite;
}

/* ===== 步骤列表 ===== */
.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 20px;
}

.progress-step {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  opacity: 0.6;
  transition: all 0.3s ease;
}

.progress-step.active {
  opacity: 1;
}

.progress-step.completed {
  opacity: 1;
}

.progress-step.error {
  opacity: 1;
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.3s ease;
  background: #e2e8f0;
  color: #64748b;
}

.progress-step.completed .step-dot {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.progress-step.active .step-dot {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

.progress-step.error .step-dot {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.step-dot svg {
  width: 16px;
  height: 16px;
}

.step-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: step-spin 0.8s linear infinite;
}

.step-line {
  width: 2px;
  height: 20px;
  background: #e2e8f0;
  transition: all 0.3s;
}

.progress-step.completed .step-line {
  background: linear-gradient(180deg, #10b981, #e2e8f0);
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 2px;
}

.step-name {
  font-weight: 600;
  color: #334155;
  font-size: 0.95rem;
}

.step-desc {
  font-size: 0.8rem;
  color: #94a3b8;
}

.step-detail {
  font-size: 0.75rem;
  color: #6366f1;
  margin-top: 2px;
}

/* ===== 日志区域 ===== */
.progress-logs {
  margin-top: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.clear-logs {
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 0.8rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.clear-logs:hover {
  background: #e2e8f0;
  color: #334155;
}

.logs-content {
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: #ffffff;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  font-size: 0.85rem;
  border-bottom: 1px solid #f1f5f9;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #94a3b8;
  font-family: monospace;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.log-message {
  color: #334155;
  word-break: break-all;
}

.log-item.success .log-message {
  color: #059669;
}

.log-item.error .log-message {
  color: #dc2626;
}

.log-item.warning .log-message {
  color: #d97706;
}

/* ===== 配置区域 ===== */
.config-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.section-icon {
  font-size: 0.92rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group.full-width {
  grid-column: span 2;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 0.9rem;
  color: #334155;
}

.label-icon {
  font-size: 0.95rem;
}

.input-wrapper {
  position: relative;
}

.input-field {
  width: 100%;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #334155;
  font-size: 0.88rem;
  transition: all 0.3s ease;
}

.input-field:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.input-hint {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 8px;
  border-radius: 4px;
}

.select-wrapper {
  position: relative;
}

.select-wrapper::after {
  content: '▼';
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.7rem;
  pointer-events: none;
}

.form-group small {
  color: #94a3b8;
  font-size: 0.8rem;
}

/* 模型大小选项 */
.model-size-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.size-option {
  position: relative;
  padding: 16px;
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.size-option:hover {
  border-color: #cbd5e1;
}

.size-option.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.size-option input {
  position: absolute;
  opacity: 0;
}

.size-badge {
  display: block;
  font-weight: 600;
  font-size: 1rem;
  color: #334155;
  margin-bottom: 4px;
}

.size-desc {
  display: block;
  font-size: 0.75rem;
  color: #64748b;
}

/* 开关样式 */
.checkbox-group {
  grid-column: span 1;
}

.toggle-label {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e2e8f0;
}

.toggle-label:hover {
  background: #f1f5f9;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 26px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #cbd5e1;
  border-radius: 26px;
  transition: 0.3s;
}

.toggle-slider::before {
  position: absolute;
  content: '';
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

input:checked + .toggle-slider {
  background: #6366f1;
}

input:checked + .toggle-slider::before {
  transform: translateX(22px);
}

.toggle-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-title {
  font-weight: 600;
  color: #334155;
}

.toggle-desc {
  font-size: 0.8rem;
  color: #64748b;
}

/* ===== 高级配置 ===== */
.advanced-config {
  margin-bottom: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
}

.advanced-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.3s ease;
}

.advanced-header:hover {
  background: #f1f5f9;
}

.advanced-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #334155;
}

.advanced-badge {
  padding: 2px 8px;
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.advanced-arrow {
  width: 20px;
  height: 20px;
  color: #94a3b8;
  transition: transform 0.3s ease;
}

.advanced-arrow.open {
  transform: rotate(180deg);
}

.advanced-content {
  padding: 20px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
}

/* 滑块样式 */
.slider-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider {
  flex: 1;
  -webkit-appearance: none;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  background: #6366f1;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.3);
}

.slider-value {
  min-width: 40px;
  text-align: right;
  font-size: 0.85rem;
  font-weight: 600;
  color: #6366f1;
}

/* 子区域标题 */
.subsection-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 3px solid #6366f1;
}

.augmentation-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #e2e8f0;
}

/* 预设按钮 */
.preset-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #e2e8f0;
}

.preset-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.btn-preset {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  color: #334155;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-preset:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.btn-preset span {
  font-size: 0.75rem;
  font-weight: 400;
  color: #64748b;
}

.preset-fast {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.preset-balanced {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.preset-accuracy {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.05);
}

.preset-kaggle {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

/* ===== 按钮样式 ===== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn svg {
  width: 18px;
  height: 18px;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

.btn-success {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.btn-success:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.25);
}

.btn-ghost {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.btn-ghost:hover:not(:disabled) {
  background: #e2e8f0;
  color: #475569;
}

.btn-large {
  width: 100%;
  padding: 16px;
  font-size: 1rem;
}

.btn-small {
  padding: 8px 16px;
  font-size: 0.85rem;
}

.btn-small svg {
  width: 14px;
  height: 14px;
}

.btn-upload {
  flex: 1;
  padding: 14px 24px;
}

.btn-cancel {
  padding: 14px 24px;
}

.btn-cancel-upload {
  width: 100%;
  margin-top: 16px;
}

.upload-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

/* ===== 消息提示 ===== */
.message-toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  margin-top: 20px;
  animation: slideIn 0.3s ease-out;
}

.message-toast.success {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #059669;
}

.message-toast.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #dc2626;
}

.toast-icon svg {
  width: 20px;
  height: 20px;
}

/* ===== 上传提示 ===== */
.upload-prompt {
  border: 2px solid rgba(99, 102, 241, 0.3);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.03));
}

.upload-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.success-icon {
  font-size: 2.5rem;
}

.upload-title h4 {
  margin: 0 0 4px;
  font-size: 1.25rem;
  color: #1e293b;
}

.upload-title p {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.model-preview {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.preview-item {
  background: rgba(255, 255, 255, 0.8);
  padding: 16px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.preview-label {
  font-size: 0.8rem;
  color: #64748b;
}

.preview-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #334155;
}

.preview-value.highlight {
  color: #6366f1;
  font-size: 1.25rem;
}

/* ===== 模型库 ===== */
.models-section .model-count {
  padding: 4px 12px;
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 1.1rem;
  margin: 0 0 8px;
  color: #475569;
}

.empty-state span {
  font-size: 0.9rem;
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.model-item:hover {
  border-color: #cbd5e1;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.model-item.active {
  background: rgba(99, 102, 241, 0.05);
  border-color: rgba(99, 102, 241, 0.3);
}

.model-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.model-avatar {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.2rem;
  color: white;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-name {
  font-weight: 600;
  color: #334155;
}

.model-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-score {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85rem;
  color: #059669;
  font-weight: 600;
}

.score-icon {
  font-size: 0.9rem;
}

.cloud-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.cloud-badge.uploaded {
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

.cloud-badge.local {
  background: #f1f5f9;
  color: #64748b;
}

.model-actions {
  display: flex;
  gap: 8px;
}

.current-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
}

.current-badge svg {
  width: 14px;
  height: 14px;
}

/* ===== 动画类 ===== */
.spin {
  animation: spin 1s linear infinite;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .page-header h1 {
    font-size: 1.75rem;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .form-group.full-width {
    grid-column: span 1;
  }
  
  .model-size-options {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .model-preview {
    grid-template-columns: 1fr;
  }
  
  .upload-actions {
    flex-direction: column;
  }
  
  .model-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .model-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .preset-buttons {
    grid-template-columns: 1fr;
  }
  svv
  .download-steps {
    flex-wrap: wrap;
    gap: 16px;
  }
}

.dataset-selector-card {
  border: 2px solid rgba(99, 102, 241, 0.2);
}

.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dataset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dataset-item:hover {
  border-color: #cbd5e1;
  transform: translateX(4px);
}

.dataset-item.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.dataset-item.cached {
  border-left: 4px solid #10b981;
}

.dataset-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.dataset-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border-radius: 10px;
}

.dataset-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dataset-name {
  font-weight: 600;
  color: #334155;
}

.dataset-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cache-tag {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.cache-tag.local {
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
}

.cache-tag.cloud {
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

.stats-tag {
  font-size: 0.8rem;
  color: #64748b;
}

.dataset-status svg {
  width: 20px;
  height: 20px;
  color: #6366f1;
}

.empty-datasets {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}

.empty-datasets p {
  margin: 0 0 8px;
  font-size: 1.1rem;
  color: #475569;
}

.empty-datasets p {
  margin: 0 0 8px;
  font-size: 1.1rem;
  color: #475569;
}

/* ===== 数据集搜索 ===== */
.dataset-search {
  position: relative;
  width: 100%;
  max-width: 100%;
  margin-bottom: 12px;
  box-sizing: border-box;
  overflow: hidden;
}

.dataset-search-input {
  display: block;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;

  padding: 10px 12px 10px 36px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #334155;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.dataset-search-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  opacity: 0.5;
}

/* ===== 数据集列表容器 - 限制高度可滚动 ===== */
.dataset-list-container {
  max-height: 320px;
  overflow-y: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.dataset-list-container::-webkit-scrollbar {
  width: 6px;
}

.dataset-list-container::-webkit-scrollbar-track {
  background: transparent;
}

.dataset-list-container::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.dataset-list-container::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 4px;
}

/* 基础数据集特殊样式 */
.dataset-item.is-base {
  border-left: 4px solid #6366f1;
  background: rgba(99, 102, 241, 0.03);
}

.cache-tag.base {
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

/* 更多文件提示 */
.more-hint {
  color: #f59e0b;
  font-weight: 600;
  margin-left: 2px;
}

/* 数据集数量徽章 */
.dataset-count-badge {
  padding: 4px 12px;
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

/* 加载更多按钮 */
.load-more {
  padding: 12px;
  text-align: center;
  border-top: 1px solid #e2e8f0;
}

.btn-load-more {
  width: 100%;
  padding: 10px;
  font-size: 0.85rem;
}


/* 在 <style scoped> 中添加 */

.global-error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  margin-bottom: 16px;
  color: #dc2626;
  font-weight: 600;
  font-size: 0.95rem;
  animation: slideIn 0.3s ease-out;
  cursor: pointer;
  backdrop-filter: blur(10px);
}

.global-error-banner:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.15));
}

.error-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.error-close {
  margin-left: auto;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: rgba(239, 68, 68, 0.2);
  color: #dc2626;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.error-close:hover {
  background: rgba(239, 68, 68, 0.3);
}
.status-message.error-text {
  color: #dc2626;
  font-weight: 600;
}
</style>