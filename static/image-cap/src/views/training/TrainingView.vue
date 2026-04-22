<template>
  <div class="training-view">
      <GradientBackground />
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>

    <div class="content-wrapper">

      <!-- 数据集状态卡片 -->
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
            {{ datasetStatus.valid ? '就绪' : '待准备' }}
          </div>
        </div>
        
        <p class="status-message">{{ datasetStatus.message || '点击刷新检查状态' }}</p>
        
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
          @click="startTraining" 
          :disabled="!datasetStatus.valid || trainingLoading"
          class="btn btn-primary btn-large"
        >
          <svg v-if="trainingLoading" class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          {{ trainingLoading ? '启动训练引擎...' : '开始训练模型' }}
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
            <span class="preview-value highlight">{{ formatMetric(trainingStatus.latest_model.metrics && trainingStatus.latest_model.metrics.mAP50) }}</span>
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
import { ref, reactive, nextTick, onMounted } from 'vue'
import GradientBackground from '@/components/GradientBackground.vue'

const route = useRoute()

// Supabase 客户端
const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)

// 状态

const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploading = ref(false)
const uploadMode = ref('folder')

const datasetPreview = ref(null)

const folderInput = ref(null)
const zipInput = ref(null)
const API_BASE = 'http://localhost:8000/api'


// ===== 状态管理 =====
const selectedZip = ref(null)
const isDragging = ref(false)
const logsContainer = ref(null)

// 上传状态（详细）
const uploadState = reactive({
  isProcessing: false,
  stage: '', // 'uploading' | 'processing' | 'completed' | 'error'
  title: '',
  message: '',
  percent: 0,
  cancelToken: null
})

// 上传步骤
const uploadSteps = reactive([
  { name: '选择文件', desc: '验证 ZIP 格式', status: 'pending', detail: '' },
  { name: '上传云端', desc: '上传到 Supabase Storage', status: 'pending', detail: '' },
  { name: '解压处理', desc: '解析数据集结构', status: 'pending', detail: '' },
  { name: '数据验证', desc: '检查 images/ 和 labels/', status: 'pending', detail: '' },
  { name: '重新打包', desc: '生成标准 YOLO 格式', status: 'pending', detail: '' },
  { name: '保存记录', desc: '写入数据库', status: 'pending', detail: '' }
])

// 日志
const uploadLogs = reactive([])

// 数据集状态
const datasetStatus = ref({
  valid: false,
  message: '点击刷新检查数据集状态',
  details: null
})

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
  
  // 自动滚动到底部
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

// ===== 事件处理 =====
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
  
  if (file.size > 2 * 1024 * 1024 * 1024) { // 2GB
    alert('文件大小超过 2GB 限制')
    return
  }
  
  selectedZip.value = file
  addLog(`已选择文件: ${file.name} (${formatFileSize(file.size)})`)
}

// ===== 上传核心逻辑 =====
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
    const projectId = route.query.projectId || 'default'
    const timestamp = new Date().toISOString().slice(0,19).replace(/[:T]/g, '-')
    const datasetId = `${projectId}_local_${timestamp}`
    const storagePath = `projects/${projectId}/uploads/${datasetId}.zip`

    addLog(`开始上传: ${storagePath}`)

    // 创建取消令牌
    const abortController = new AbortController()
    uploadState.cancelToken = abortController

    // 1. 上传到 Supabase Storage（带进度）
    const { data: uploadData, error: uploadError } = await supabase.storage
      .from('datasets')
      .upload(storagePath, selectedZip.value, {
        cacheControl: '3600',
        upsert: false,
        onUploadProgress: (progress) => {
          const percent = Math.round((progress.loaded / progress.total) * 40) // 上传占 40%
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
    
    // 2. 通知后端处理
    uploadState.stage = 'processing'
    uploadState.title = '服务器处理中'
    uploadState.message = '正在解析数据集...'
    uploadState.percent = 45

    addLog('开始后端处理...')

    const response = await fetch('/api/dataset/process-from-storage', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        project_id: projectId,
        dataset_name: `local_dataset_${timestamp}`,
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
    
    // 模拟处理进度（实际可以从后端获取）
    await simulateProcessingProgress()

    // 完成
    uploadState.stage = 'completed'
    uploadState.title = '上传成功'
    uploadState.message = `数据集包含 ${result.stats?.total || 0} 张图片`
    uploadState.percent = 100
    
    updateStep(2, 'completed')
    updateStep(3, 'completed')
    updateStep(4, 'completed')
    updateStep(5, 'completed', `ID: ${result.dataset_id}`)

    addLog(`处理完成: ${result.message}`, 'success')

    // 刷新状态
    setTimeout(async () => {
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
      
      // 标记当前步骤为错误
      const currentStep = uploadSteps.findIndex(s => s.status === 'active')
      if (currentStep >= 0) updateStep(currentStep, 'error')
    }
  }
}

// 模拟处理进度（实际项目中可以从后端 WebSocket 获取真实进度）
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












// 验证 YOLO 格式
const validateYOLOFormat = (structure) => {
  return structure.images.length > 0 && structure.labels.length > 0
}

// 生成预览
const generatePreview = async (structure, files) => {
  const classes = new Set()
  let labelCount = 0

  // 读取 labels 文件统计类别
  for (const labelFile of structure.labels.slice(0, 100)) { // 只读取前100个
    try {
      const text = await readFileText(labelFile)
      const lines = text.trim().split('\n')
      labelCount += lines.length
      
      for (const line of lines) {
        const classId = line.trim().split(' ')[0]
        if (classId !== undefined) {
          classes.add(`class_${classId}`)
        }
      }
    } catch (e) {
      console.warn('读取标签文件失败:', e)
    }
  }

  return {
    imageCount: structure.images.length,
    labelCount,
    classes: Array.from(classes).sort(),
    structure
  }
}

// 读取文件文本
const readFileText = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = reject
    
    if (file.getContent) {
      file.getContent().then(blob => reader.readAsText(blob))
    } else {
      reader.readAsText(file)
    }
  })
}
// 确认上传 - 修复版
const confirmUpload = async () => {
  if (!datasetPreview.value) return

  uploading.value = true
  uploadProgress.value = 0

  try {
    const projectId = route.query.projectId || 'default'
    
    // 创建 FormData - 注意顺序：先添加普通字段，再添加文件
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('dataset_name', `local_dataset_${new Date().toISOString().slice(0,10)}`)
    
    // 获取所有文件
    const structure = datasetPreview.value.structure
    const allFiles = [
      ...structure.images,
      ...structure.labels,
      ...(structure.rootFiles || [])
    ]

    console.log(`准备上传 ${allFiles.length} 个文件`)

    // 处理每个文件
    let uploadedCount = 0
    for (let i = 0; i < allFiles.length; i++) {
      const file = allFiles[i]
      
      // 获取正确的路径 - 这是关键！
      let relativePath = file.webkitRelativePath || file.path || file.name
      
      // 确保路径格式正确（移除开头的斜杠）
      relativePath = relativePath.replace(/^\//, '')
      
      console.log(`处理文件 ${i}: ${relativePath}`)

      try {
        // 如果是从ZIP解压的文件（有getContent方法）
        if (file.getContent && typeof file.getContent === 'function') {
          const blob = await file.getContent()
          // 直接使用 blob，但指定 filename
          formData.append('files', blob, relativePath)
        } else {
          // 普通文件上传 - 直接使用原文件
          formData.append('files', file, relativePath)
        }
        uploadedCount++
      } catch (err) {
        console.warn(`文件 ${relativePath} 处理失败:`, err)
      }
      
      uploadProgress.value = Math.round(((i + 1) / allFiles.length) * 100)
    }

    // 检查是否有文件被添加
    if (uploadedCount === 0) {
      throw new Error('没有有效的文件可以上传')
    }
    
    console.log(`实际准备上传 ${uploadedCount} 个文件`)

    // 关键：不要手动设置 Content-Type！
    // 浏览器会自动设置 multipart/form-data 并包含 boundary
    const response = await fetch('/api/dataset/upload-local', {
      method: 'POST',
      body: formData
      // 不要添加 headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('服务器响应:', errorText)
      throw new Error(`上传失败: ${response.status} - ${errorText}`)
    }

    const result = await response.json()
    
    alert(`✅ 上传成功！\n图片: ${result.stats?.total || 'N/A'}\n类别: ${result.stats?.classes || 'N/A'}`)
    
    // 刷新状态
    await checkDataset()
    
    // 清空预览
    datasetPreview.value = null
    
  } catch (e) {
    console.error('上传错误:', e)
    alert('上传失败: ' + e.message)
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}


// 模型大小选项
const modelSizes = [
  { value: 'auto', label: 'Auto', desc: '智能选择最佳模型' },
  { value: 'n', label: 'Nano', desc: '极速训练，低精度' },
  { value: 's', label: 'Small', desc: '快速训练，中等精度' },
  { value: 'm', label: 'Medium', desc: '平衡速度与精度' },
  { value: 'l', label: 'Large', desc: '高精度，较慢' },
  { value: 'x', label: 'XLarge', desc: '最高精度，最慢' }
]


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

// 配置 - 包含高级选项
const config = ref({
  // 基础配置
  epochs: 100,
  batch: 16,
  model_size: 'auto',
  augmentation: true,
  incremental: false,
  
  // 高级配置
  optimizer: 'AdamW',
  lr0: 0.001,
  imgsz: 640,
  patience: 20,
  weight_decay: 0.0005,
  dropout: 0.0,
  label_smoothing: 0.0,
  freeze: 0,
  warmup_epochs: 3,
  
  // 数据增强
  mosaic: 1.0,
  mixup: 0.1,
  copy_paste: 0.0,
  degrees: 15,
  scale: 0.5,
  shear: 5
})

// 预设配置
const presets = {
  fast: {
    epochs: 50,
    batch: 16,
    imgsz: 640,
    patience: 10,
    lr0: 0.001,
    optimizer: 'AdamW',
    freeze: 10,
    dropout: 0,
    augmentation: true,
    mosaic: 0.5,
    mixup: 0,
    degrees: 5,
    scale: 0.3
  },
  balanced: {
    epochs: 100,
    batch: 16,
    imgsz: 640,
    patience: 20,
    lr0: 0.001,
    optimizer: 'AdamW',
    freeze: 0,
    dropout: 0.05,
    augmentation: true,
    mosaic: 1.0,
    mixup: 0.1,
    degrees: 15,
    scale: 0.5
  },
  accuracy: {
    epochs: 200,
    batch: 8,
    imgsz: 800,
    patience: 30,
    lr0: 0.0005,
    optimizer: 'AdamW',
    freeze: 0,
    dropout: 0.1,
    label_smoothing: 0.05,
    augmentation: true,
    mosaic: 1.0,
    mixup: 0.3,
    copy_paste: 0.2,
    degrees: 20,
    scale: 0.6,
    shear: 8
  },
  kaggle: {
    epochs: 80,
    batch: 6,
    imgsz: 800,
    patience: 20,
    lr0: 0.001,
    optimizer: 'AdamW',
    freeze: 0,
    dropout: 0.1,
    weight_decay: 0.0005,
    label_smoothing: 0.05,
    augmentation: true,
    mosaic: 1.0,
    mixup: 0.3,
    copy_paste: 0.4,
    degrees: 15,
    scale: 0.6,
    shear: 5,
    warmup_epochs: 5
  }
}

const applyPreset = (presetName) => {
  const preset = presets[presetName]
  if (preset) {
    Object.assign(config.value, preset)
    // 如果预设包含 augmentation，确保开关打开
    if (preset.augmentation !== undefined) {
      config.value.augmentation = preset.augmentation
    }
  }
}

const formatMetric = (value) => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

const checkDataset = async () => {
   checking.value = true
  try {
    const projectId = route.query.projectId || 'default'
    const res = await fetch(`/api/dataset/status/${projectId}`)
    const data = await res.json()
    
    // 适配后端返回格式
    const dataset = data.dataset || data.datasets?.[0] || {}
    const stats = data.stats || dataset.stats || {}
    
    // BUG 修复：使用正确的变量 data/dataset，而不是未定义的 datasetData
    datasetStatus.value = {
      valid: data.status === 'ready' || dataset.status === 'ready', 
      message: data.message || dataset.status || '数据集状态未知',
      details: {
        stats: stats,
        dataset_id: dataset.dataset_id || dataset.id,
        storage_path: dataset.storage_path
      }
    }
   
    
    // 获取硬件信息和模型列表（原有逻辑）
    const hwRes = await fetch(`${API_BASE}/training/status`)
    const hwData = await hwRes.json()
    hardwareInfo.value = {
      cuda_available: hwData.cuda_available,
      cuda_device: hwData.cuda_device
    }
    
    // 更新模型列表（添加这部分）
    const allModels = [
      ...(hwData.local_models || []).map(m => ({
        name: m.name,
        displayName: m.name,
        path: m.path,
        local_path: m.path,
        model_path: null, // 本地模型没有云端路径
        map50: null, // 本地模型可能没有指标
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
    
    // 去重：如果有同名模型，优先显示云端版本（因为有更多元数据）
    const modelMap = new Map()
    for (const model of allModels) {
      const key = model.name
      if (!modelMap.has(key) || model.model_path) {
        modelMap.set(key, model)
      }
    }
    models.value = Array.from(modelMap.values())
    
    // 更新当前激活的模型
    currentModel.value = hwData.current_model || ''
    
    // 更新训练状态（待上传提示）
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
    
  } catch (e) {
    datasetStatus.value = { 
      valid: false, 
      message: '检查失败: ' + e.message 
    }
  } finally {
    checking.value = false
  }
}
const quickPrepareDataset = async () => {
  try {
    // 1. 获取项目所有已完成的标注任务
    const projectId = route.query.projectId || 'default'
    const tasksRes = await fetch(`/api/projects/${projectId}/completed-tasks`)
    const tasks = await tasksRes.json()
    
    if (tasks.length === 0) {
      alert('没有已完成的标注任务')
      return
    }
    
    // 2. 调用合并 API
    const result = await prepareDatasetForTraining(
      projectId,
      tasks.map(t => t.task_id),
      {
        datasetName: `auto_dataset_${new Date().toISOString().slice(0,10)}`,
        description: `自动合并 ${tasks.length} 个标注任务`
      }
    )
    
    alert(`✅ 数据集准备完成！\n图片: ${result.stats.total}\n类别: ${result.stats.classes}`)
    
    // 3. 刷新状态
    await checkDataset()
    
  } catch (e) {
    alert('准备失败: ' + e.message)
  }
}
const startTraining = async () => {
  trainingLoading.value = true
  trainingMessage.value = null
  
  try {
    // 构建参数，包含所有高级选项
    const params = new URLSearchParams({
      epochs: config.value.epochs,
      batch: config.value.batch,
      model_size: config.value.model_size,
      augmentation: config.value.augmentation,
      // 高级参数
      optimizer: config.value.optimizer,
      lr0: config.value.lr0,
      imgsz: config.value.imgsz,
      patience: config.value.patience,
      weight_decay: config.value.weight_decay,
      dropout: config.value.dropout,
      label_smoothing: config.value.label_smoothing,
      freeze: config.value.freeze,
      warmup_epochs: config.value.warmup_epochs,
      // 增强参数
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

onMounted(() => {
  checkDataset()
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
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 8px;
  color: #1e293b;
}

.subtitle {
  color: #64748b;
  font-size: 0.92rem;
  margin: 0;
}

/* ===== 玻璃卡片 ===== */
.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 20px;
  padding: 22px;
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
  gap: 10px;
  margin-bottom: 16px;
}

.icon-wrapper {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-wrapper svg {
  width: 18px;
  height: 18px;
  color: #6366f1;
}

.card-header h3 {
  flex: 1;
  margin: 0;
  font-size: 1.08rem;
  font-weight: 600;
  color: #1e293b;
}

/* ===== 状态卡片 ===== */
.status-card {
  border-left: 4px solid #ef4444;
  margin-bottom: 12px;
}

.status-card.ready {
  border-left-color: #10b981;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.68rem;
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
  font-size: 0.86rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
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

.hardware-info {
  margin-bottom: 20px;
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

.upload-actions {
  display: flex;
  gap: 12px;
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
}


/* 添加/替换以下样式 */

/* ===== 上传数据集卡片 ===== */
.upload-dataset-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
  border: 1px solid rgba(226, 232, 240, 0.8);
  margin-top: 0;
  margin-bottom: 14px;
}

.upload-dataset-card .card-header {
  margin-bottom: 24px;
}

.upload-dataset-card .header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.upload-dataset-card .header-desc {
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

/* ===== 标签页 ===== */
.upload-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.tab-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px 16px;
  background: rgba(241, 245, 249, 0.6);
  border: 2px solid transparent;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.tab-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.08));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.tab-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.2);
}

.tab-btn:hover::before {
  opacity: 1;
}

.tab-btn.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border-color: #6366f1;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
}

.tab-btn.active::before {
  opacity: 1;
}

.tab-icon {
  font-size: 1.75rem;
  z-index: 1;
}

.tab-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #334155;
  z-index: 1;
}

.tab-hint {
  font-size: 0.75rem;
  color: #94a3b8;
  z-index: 1;
}

.tab-btn.active .tab-text {
  color: #6366f1;
}

/* ===== 拖拽上传区域 ===== */
.drop-zone {
  position: relative;
  border: 2px dashed #cbd5e1;
  border-radius: 20px;
  padding: 34px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.8));
  overflow: hidden;
}

.drop-zone::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.03), rgba(139, 92, 246, 0.03));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.drop-zone:hover {
  border-color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.1);
}

.drop-zone:hover::before {
  opacity: 1;
}

.drop-zone-inner {
  position: relative;
  z-index: 1;
}

.drop-illustration {
  position: relative;
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
}

.upload-circle {
  width: 64px;
  height: 64px;
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
  width: 26px;
  height: 26px;
  color: white;
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  border: 2px solid rgba(99, 102, 241, 0.3);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
  z-index: 1;
}

@keyframes pulse-ring {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.5);
    opacity: 0;
  }
}

.drop-text {
  margin-bottom: 16px;
}

.drop-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px;
}

.drop-subtitle {
  font-size: 0.78rem;
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
  letter-spacing: 0.5px;
}

.format-divider {
  color: #cbd5e1;
  font-size: 0.8rem;
}

/* ===== 上传进度 ===== */
.upload-progress {
  margin-top: 24px;
  padding: 20px;
  background: rgba(241, 245, 249, 0.6);
  border-radius: 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #334155;
}

.progress-percent {
  font-size: 0.9rem;
  font-weight: 700;
  color: #6366f1;
}

.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.progress-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shine 1.5s infinite;
}

@keyframes shine {
  0% { left: -100%; }
  100% { left: 100%; }
}

/* ===== 数据集预览 ===== */
.dataset-preview {
  margin-top: 24px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.8));
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.preview-header .preview-icon {
  font-size: 1.5rem;
}

.preview-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.preview-stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.6);
  transition: all 0.3s ease;
}

.preview-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.stat-icon-bg {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.images-bg {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
}

.labels-bg {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.1));
}

.classes-bg {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.1));
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
}

.stat-name {
  font-size: 0.75rem;
  color: #94a3b8;
}

.class-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.class-label {
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 500;
}

.class-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.class-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  color: #6366f1;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid rgba(99, 102, 241, 0.15);
  transition: all 0.2s ease;
}

.class-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
}

/* ===== 上传操作按钮 ===== */
.upload-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn-upload {
  flex: 1;
  padding: 14px 24px;
  font-size: 0.95rem;
}

.btn-cancel {
  padding: 14px 24px;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .upload-tabs {
    grid-template-columns: 1fr;
  }
  
  .preview-stats {
    grid-template-columns: 1fr;
  }
  
  .drop-zone {
    padding: 32px 20px;
  }
  
  .upload-actions {
    flex-direction: column;
  }
}

/* 添加 ZIP 信息样式 */
.zip-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
  border-radius: 12px;
  margin-top: 14px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.zip-icon {
  font-size: 1.5rem;
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
  font-size: 0.76rem;
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

/* ===== 基础变量与动画 ===== */
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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



/* ===== 页面标题 ===== */
.page-header {
  text-align: center;
  margin-bottom: 40px;
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
  transition: all 0.3s ease;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.glass-card:hover {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* ===== 上传数据集卡片 ===== */
.upload-dataset-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
  margin-top: 0;
  margin-bottom: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
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

.header-text {
  flex: 1;
}

.header-text h3 {
  margin: 0 0 4px;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

.header-desc {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
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
  animation: spin 2s linear infinite;
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

.progress-fill.uploading {
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

/* ===== 按钮 ===== */
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

.btn-ghost {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.btn-ghost:hover:not(:disabled) {
  background: #e2e8f0;
  color: #475569;
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

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .page-header h1 {
    font-size: 1.75rem;
  }
  
  .drop-zone {
    padding: 32px 20px;
  }
  
  .upload-actions {
    flex-direction: column;
  }
  
  .progress-header {
    flex-wrap: wrap;
  }
  
  .progress-percentage {
    width: 100%;
    text-align: right;
    margin-top: 8px;
  }
}
/* ===== 页面根容器 ===== */
.training-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f4f8 100%);
  position: relative;        /* 创建定位上下文 */
  overflow-x: hidden;
  color: #2c3e50;
}

/* ===== 内容包装器 - 必须在背景之上 ===== */
.content-wrapper {
  position: relative;      /* 启用 z-index */
  z-index: 1;              /* 确保在背景组件之上 */
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}

/* ===== 玻璃卡片样式 ===== */
.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 20px;
  padding: 28px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

</style>
