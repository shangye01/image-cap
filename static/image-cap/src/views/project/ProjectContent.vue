<template>
  <div class="project-content-page">
    <div class="page-top-actions">
      <TeamCollaborationActions
        :project-id="currentProject?.id || ''"
        :project-name="currentProject?.projectName || ''"
        :project-options="
          projectList.map((item) => ({
            id: item.id,
            name: item.projectName,
            isSharedCopy: item.isSharedCopy,
          }))
        "
      />
    </div>
    <!-- 1. 项目列表页 -->
    <template v-if="!currentProject">
      <div class="project-toolbar">
        <div class="toolbar-left">
          <input
            v-model="searchKeyword"
            class="toolbar-input"
            type="text"
            placeholder="搜索项目名"
          />
          <input
            v-model="teamSearchKeyword"
            class="toolbar-input team-toolbar-input"
            type="text"
            placeholder="按团队搜索（团队创建/分享）"
          />

          <select v-model="sortType" class="toolbar-select">
            <option value="created_desc">按创建时间（新到旧）</option>
            <option value="created_asc">按创建时间（旧到新）</option>
            <option value="name_asc">按项目名（A-Z）</option>
            <option value="name_desc">按项目名（Z-A）</option>
          </select>
        </div>

        <div class="toolbar-right">
          <div class="project-count">共 {{ filteredProjectList.length }} 个项目</div>
        </div>
      </div>

      <div class="project-grid">
        <CreateBoardCard
          :existing-project-names="projectList.map((item) => item.projectName)"
          @create="handleCreateProject"
        />

        <div
          v-for="project in filteredProjectList"
          :key="project.id"
          class="project-folder-card"
          :class="{
            'project-folder-card--shared': project.isSharedCopy,
            'project-folder-card--shared-pending': project.isSharedCopy && !project.shareAcceptedAt,
          }"
          @mouseenter="showRemark(project.id)"
          @mouseleave="hideRemark"
        >
          <div class="project-card-menu-wrap">
            <button
              class="project-menu-trigger"
              type="button"
              @click.stop="toggleProjectMenu(project.id)"
            >
              ⋯
            </button>

            <transition name="menu-fade">
              <div v-if="openedProjectMenuId === project.id" class="project-menu-dropdown">
                <button
                  class="project-menu-item"
                  type="button"
                  @click.stop="handleRenameFromMenu(project)"
                >
                  重命名
                </button>
                <button
                  class="project-menu-item danger"
                  type="button"
                  @click.stop="handleDeleteFromMenu(project.id)"
                >
                  删除
                </button>
              </div>
            </transition>
          </div>

          <div class="folder-click-area" @click="enterProject(project)">
            <div class="folder-preview">
              <div
                v-if="showProjectReviewDot(project)"
                class="project-review-dot"
                :title="`待审核 ${getProjectPendingReviewCount(project)} 项`"
              ></div>
              <transition name="mask-fade">
                <div
                  v-if="hoveredProjectId === project.id && project.remark"
                  class="folder-remark-mask"
                >
                  <div class="folder-remark-text">
                    {{ project.remark }}
                  </div>
                </div>
              </transition>

              <div class="folder-shape">
                <div class="folder-tab"></div>
              </div>
            </div>

            <div class="folder-name">
              {{ project.projectName }}
            </div>

            <div v-if="project.isSharedCopy" class="shared-project-badge">
              已分享给我 · 来自 {{ project.sharedBy || '团队成员' }}
            </div>
            <div v-if="project.organizationNickname" class="project-team-badge">
              团队：{{ project.organizationNickname }}
            </div>
            <div
              v-if="project.isSharedCopy && !project.shareAcceptedAt"
              class="project-pending-acceptance"
            >
              待接收：点击进入后正式接收
            </div>

            <div class="folder-meta">
              <span>{{ project.mode === 'keyword' ? '关键词模型' : '非关键词模型' }}</span>
              <span>{{ formatDate(project.createdAt) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!filteredProjectList.length" class="empty-project-state">没有匹配的项目</div>
    </template>

    <!-- 2. 项目内部：文件夹列表页 -->
    <template v-else-if="currentProject && !currentFolder">
      <div class="project-detail-header">
        <div class="project-nav">
          <button
            class="back-btn"
            type="button"
            @click="backToProjectList"
            aria-label="返回项目列表"
          >
            <span class="back-btn-icon">←</span>
          </button>

          <div class="breadcrumb">
            <span class="breadcrumb-link" @click="backToProjectList">项目列表</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ currentProject.projectName }}</span>
          </div>
        </div>

        <div class="project-detail-title-wrap">
          <div class="project-detail-title-row">
            <div class="project-detail-title">{{ currentProject.projectName }}</div>
            <button
              v-if="showPendingReviewButton"
              type="button"
              class="pending-review-btn"
              @click="openPendingReviewDialog"
            >
              待审核
              <span v-if="pendingReviewCount > 0" class="pending-review-badge">{{
                pendingReviewCount
              }}</span>
            </button>
          </div>

          <div v-if="currentProject.remark" class="project-detail-remark">
            {{ currentProject.remark }}
          </div>
        </div>
      </div>

      <div class="project-grid">
        <div
          v-for="folder in currentProject.folders"
          :key="folder.id"
          class="project-folder-card child-folder-card"
          @click="enterFolder(folder)"
        >
          <div class="folder-preview small-folder-preview">
            <div class="folder-shape">
              <div class="folder-tab"></div>
            </div>
          </div>

          <div class="folder-name">
            {{ folder.name }}
          </div>

          <div class="folder-count">{{ folder.files.length }} 个文件</div>
        </div>
      </div>
    </template>

    <!-- 3. 文件夹内部：图片文件宫格页 -->
    <template v-else-if="currentProject && currentFolder">
      <div class="project-detail-header">
        <div class="project-nav">
          <button
            class="back-btn"
            type="button"
            @click="backToFolderList"
            aria-label="返回文件夹列表"
          >
            <span class="back-btn-icon">←</span>
          </button>

          <div class="breadcrumb">
            <span class="breadcrumb-link" @click="backToProjectList">项目列表</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-link" @click="backToFolderList">
              {{ currentProject.projectName }}
            </span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ currentFolder.name }}</span>
          </div>
        </div>

        <div class="project-detail-title-wrap">
          <div class="project-detail-title-row">
            <div class="project-detail-title">{{ currentFolder.name }}</div>
            <div class="folder-action-buttons">
              <!-- 待标注文件夹：原有逻辑 -->
              <template v-if="isPendingFolder">
                <button type="button" class="file-action-btn batch" @click="selectAllFilesInFolder">
                  批量标注
                </button>
                <button type="button" class="file-action-btn work" @click="startSelectedWork">
                  开始标注
                </button>
              </template>

              <!-- 标注中文件夹：继续标注 -->
              <template v-else-if="isLabelingFolder">
                <button type="button" class="file-action-btn batch" @click="selectAllFilesInFolder">
                  批量选择
                </button>
                <button
                  type="button"
                  class="file-action-btn work continue-btn"
                  @click="continueLabeling"
                  :disabled="labelingTasks.length === 0"
                >
                  {{
                    labelingTasks.length > 0 ? `继续标注 (${labelingTasks.length})` : '暂无标注任务'
                  }}
                </button>
              </template>

              <!-- 已标注文件夹：查看 -->
              <template v-else-if="isDoneFolder">
                <button type="button" class="file-action-btn batch" @click="selectAllFilesInFolder">
                  批量选择
                </button>
                <button
                  type="button"
                  class="file-action-btn work export-btn"
                  @click="openExportDialog"
                  :disabled="currentFolder.files.length === 0"
                >
                  📥 数据导出
                </button>
              </template>
            </div>
          </div>

          <div class="project-detail-remark">共 {{ currentFolder.files.length }} 个文件</div>
        </div>
      </div>

      <div v-if="currentFolder.files.length" class="image-grid">
        <div
          v-for="file in currentFolder.files"
          :key="file.id"
          v-memo="[file.id, file.status, selectedFileIdSet.has(file.id)]"
          class="image-card"
        >
          <label class="file-select-checkbox" @click.stop>
            <input
              type="checkbox"
              :checked="selectedFileIdSet.has(file.id)"
              @change="toggleFileSelection(file.id)"
            />
          </label>
          <div class="image-card-preview" @click.stop="handleImagePreview(file)">
            <template v-if="isImageFile(file)">
              <img
                v-lazy="getFilePreviewUrl(file)"
                :data-file-id="file.id"
                :alt="file.name"
                class="image-thumb"
                loading="lazy"
              />
            </template>
          </div>
        </div></div
    ></template>
  </div>
</template>

            <template v-else-if="isImageFile(file)">
  <div class="image-placeholder">图片不可预览</div>
</template>

            <template v-else>
  <div class="file-placeholder">📄</div>
</template>
          </div>

          <div class="image-card-info">
            <div class="file-name-text" :title="file.name">{{ file.name }}</div>
            <div v-if="file.status" class="file-status-tag" :class="file.status">
              {{ getStatusText(file.status) }}
            </div>
          </div>

          <div class="image-card-actions">
            <!-- 已标注文件夹：只显示查看标注 -->
            <template v-if="isDoneFolder">
  <button
    type="button"
    class="file-action-btn work review-btn"
    @click.stop="
      openAnnotationPreview(
        file,
        currentFolder.files.findIndex((f) => f.id === file.id)
      )
    "
    style="width: 100%"
  >
    🔍 查看标注
  </button>
</template>

            <!-- 标注中文件夹：预览打开大图标注弹窗，工作按钮继续标注 -->
            <template v-else-if="isLabelingFolder">
  <button
    type="button"
    class="file-action-btn preview"
    @click.stop="
      openAnnotationPreview(
        file,
        currentFolder.files.findIndex((f) => f.id === file.id)
      )
    "
  >
    🔍 预览标注
  </button>
  <button type="button" class="file-action-btn work continue-btn" @click.stop="handleWork(file)">
    {{ getWorkButtonText }}
  </button>
</template>

            <!-- 待标注文件夹：原有逻辑 -->
            <template v-else>
  <button type="button" class="file-action-btn preview" @click.stop="previewFile(file)">
    预览
  </button>
  <button type="button" class="file-action-btn work" @click.stop="handleWork(file)">
    {{ getWorkButtonText }}
  </button>
</template>
          </div>
        </div>
      </div>

      <div v-else class="empty-folder-page">{{ getEmptyFolderText }}</div>
    </template>

    <!-- 工作弹窗 - 仅待标注文件夹使用 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="workVisible" class="dialog-mask" @click="closeWorkDialog">
          <div class="dialog-panel work-dialog-panel" @click.stop>
            <div class="work-dialog-header">
              <div class="dialog-title">开始标注</div>
              <button class="work-dialog-close" type="button" @click="closeWorkDialog">×</button>
            </div>

            <div class="dialog-body work-dialog-body">
              <div class="work-file-summary">
                {{ workSummaryText }}
              </div>

              <div class="mode-row">
                <label class="radio-item" @click="workForm.mode = 'keyword'">
                  <span class="radio-dot" :class="{ active: workForm.mode === 'keyword' }"></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'keyword' }">
                    关键词模型
                  </span>
                </label>

                <label class="radio-item" @click="workForm.mode = 'nonKeyword'">
                  <span
                    class="radio-dot"
                    :class="{ active: workForm.mode === 'nonKeyword' }"
                  ></span>
                  <span class="radio-text" :class="{ strong: workForm.mode === 'nonKeyword' }">
                    非关键词模型
                  </span>
                </label>
              </div>

              <div v-if="workForm.mode === 'keyword'" class="tag-panel">
                <div class="selected-title">已选择的标签</div>

                <div class="selected-box">
                  <template v-if="workSelectedTags.length">
                    <div
                      v-for="tag in workSelectedTags"
                      :key="tag.id"
                      class="tag-chip selected"
                      :style="{ backgroundColor: tag.color }"
                    >
                      <span>{{ tag.name }}</span>
                      <button class="tag-remove" type="button" @click="removeWorkTag(tag.id)">
                        ×
                      </button>
                    </div>
                  </template>

                  <div v-else class="empty-text">请选择下方标签</div>
                </div>

                <div v-for="scene in scenes" :key="scene.id" class="scene-block">
                  <div class="scene-title">{{ scene.name }}</div>

                  <div class="scene-tags">
                    <button
                      v-for="tag in scene.tags"
                      :key="tag.id"
                      type="button"
                      class="tag-chip scene-chip"
                      :class="{ active: isWorkSelected(tag.id) }"
                      :style="{ backgroundColor: tag.color }"
                      @click="toggleWorkTag(tag)"
                    >
                      <span>{{ tag.name }}</span>
                      <span v-if="isWorkSelected(tag.id)" class="tag-remove small">×</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
               <!-- 置信度阈值设置 -->
            <div class="confidence-section">
              <div class="confidence-header">
                <span class="confidence-title">🎯 置信度阈值</span>
                <span class="confidence-value">{{ Math.round(workForm.confidenceThreshold * 100) }}%</span>
              </div>
              <div class="confidence-desc">只保留置信度高于此值的目标检测结果</div>
              <div class="slider-container">
                <el-slider
                  v-model="workForm.confidenceThreshold"
                  :min="0.05"
                  :max="0.95"
                  :step="0.05"
                  :show-tooltip="false"
                  :marks="{0.25: '25%', 0.5: '50%', 0.75: '75%'}"
                />
              </div>
              <div class="confidence-hint">
                <span class="hint-low">低阈值 → 更多结果</span>
                <span class="hint-high">高阈值 → 更精准</span>
              </div>
            </div>
            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="closeWorkDialog">
                取消
              </button>
              <button class="dialog-btn primary" type="button" @click="confirmWorkDialog">
                确定
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- 重命名弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="renameVisible" class="dialog-mask" @click="closeRenameDialog">
          <div class="dialog-panel" @click.stop>
            <div class="dialog-title">重命名项目</div>

            <div class="dialog-body">
              <input
                v-model="renameValue"
                class="dialog-input"
                type="text"
                placeholder="请输入新的项目名"
              />

              <div v-if="renameError" class="dialog-error">
                {{ renameError }}
              </div>
            </div>

            <div class="dialog-footer">
              <button class="dialog-btn secondary" type="button" @click="closeRenameDialog">
                取消
              </button>
              <button class="dialog-btn primary" type="button" @click="confirmRename">确定</button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- 图片预览弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="previewVisible" class="preview-mask" @click="closePreview">
          <div class="preview-panel" @click.stop>
            <button class="preview-close-btn" type="button" @click="closePreview">×</button>

            <div class="preview-content">
              <img
                v-if="previewImageUrl"
                :src="previewImageUrl"
                :alt="previewFileName"
                class="preview-image"
              />
            </div>

            <div class="preview-footer">
              <div class="preview-file-name">{{ previewFileName }}</div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>

  <!-- 大图标注预览弹窗 -->
  <teleport to="body">
    <transition name="preview-fade">
      <div
        v-if="annotationPreviewVisible"
        class="annotation-preview-mask"
        @click="closeAnnotationPreview"
        @keydown="handlePreviewKeydown"
        tabindex="0"
        ref="previewMaskRef"
      >
        <!-- 左侧切换按钮 -->
        <button v-if="canGoPrev" class="nav-arrow nav-prev" @click.stop="goToPrevImage">‹</button>

        <div class="annotation-preview-panel" @click.stop>
          <!-- 顶部工具栏 -->
          <div class="preview-toolbar">
            <div class="toolbar-info">
              <span class="file-counter"
                >{{ currentPreviewIndex + 1 }} / {{ previewableFiles.length }}</span
              >
              <span class="file-name">{{ annotationPreviewFileName }}</span>
            </div>

            <div class="toolbar-actions">
              <button
                v-if="isLabelingFolder && currentPreviewTask"
                type="button"
                class="toolbar-btn btn-continue"
                @click.stop="continueFromPreview"
              >
                ✏️ 继续标注
              </button>
              <button
                type="button"
                class="toolbar-btn btn-close"
                @click.stop="closeAnnotationPreview"
              >
                ✕
              </button>
            </div>
          </div>

          <!-- 图片内容区 -->
          <div
            class="annotation-preview-content"
            ref="swipeAreaRef"
            @touchstart="handleTouchStart"
            @touchend="handleTouchEnd"
          >
            <div class="annotation-image-wrapper" ref="imageWrapperRef">
              <!-- 使用计算后的尺寸容器 -->
              <div class="annotation-image-container" :style="imageContainerStyle">
                <img
                  v-if="annotationPreviewImageUrl"
                  :src="annotationPreviewImageUrl"
                  :alt="annotationPreviewFileName"
                  class="annotation-preview-image"
                  @load="onAnnotationImageLoad"
                  ref="previewImageRef"
                  draggable="false"
                />
                  
                <!-- SVG 标注层 - 与容器完全重叠 -->
               <!-- 优化后的 SVG 标签渲染 -->
               <svg
    v-if="annotationImageLoaded && currentAnnotations.length > 0"
    class="annotation-overlay"
    :viewBox="`0 0 ${annotationImageNaturalWidth} ${annotationImageNaturalHeight}`"
    preserveAspectRatio="none"
  >
    <g v-for="(anno, index) in currentAnnotations" :key="`box-${index}`">
      <rect
  v-for="(anno, index) in currentAnnotations"
  :key="`box-${index}`"
  :x="anno.x"
  :y="anno.y"
  :width="anno.width"
  :height="anno.height"
  fill="none"
  :stroke="anno.color || '#ff4444'" 
  stroke-width="2"
  rx="2"
/>
    </g>
  </svg>
   <div
    v-if="annotationImageLoaded && currentAnnotations.length > 0"
    class="annotation-labels-layer"
  >
    <div
  v-for="(anno, index) in currentAnnotations"
  :key="`label-${index}`"
  class="annotation-label"
  :class="{ 'label-below': isLabelBelow(anno) }"
  :style="getLabelStyle(anno)"
>
  <span class="label-text">{{ anno.label || '未命名' }}</span>
</div>
 
</div>

              </div>
            </div>
          </div>

          <!-- 底部信息栏 -->
          <div class="annotation-preview-footer">
            <div class="annotation-stats">
              <span v-if="currentAnnotations.length > 0" class="stat-item">
                📦 {{ currentAnnotations.length }} 个标注
              </span>
              <span v-else class="stat-item empty">暂无标注</span>

              <span v-if="annotationDataSource" class="stat-item source">
                来源: {{ annotationDataSource }}
              </span>
            </div>

            <div v-if="annotationLabels.length > 0" class="annotation-label-list">
              <span v-for="label in annotationLabels" :key="label" class="annotation-label-chip">
                🏷️ {{ label }}
              </span>
            </div>
          </div>
        </div>

        <!-- 右侧切换按钮 -->
        <button v-if="canGoNext" class="nav-arrow nav-next" @click.stop="goToNextImage">›</button>
      </div>
    </transition>
  </teleport>

  <PendingReviewDialog
    :visible="pendingReviewVisible"
    :items="pendingReviewItems"
    @close="closePendingReviewDialog"
    @select="openPendingReviewItem"
  />
   <!-- 数据导出弹窗 -->
    <teleport to="body">
      <transition name="preview-fade">
        <div v-if="exportVisible" class="dialog-mask" @click="closeExportDialog">
          <div class="dialog-panel export-dialog-panel" @click.stop>
            <div class="export-dialog-header">
              <div class="dialog-title">📦 导出标注数据</div>
              <button class="export-dialog-close" type="button" @click="closeExportDialog">×</button>
            </div>

            <div class="dialog-body export-dialog-body">
              <div class="export-summary">
                <span class="export-count">共 {{ selectedFilesForExport.length }} 个文件待导出</span>
                <span v-if="selectedFilesForExport.length === 0" class="export-hint">将导出文件夹内所有已标注文件</span>
              </div>

              <!-- 导出格式选择 -->
              <div class="export-format-section">
                <div class="section-title">选择导出格式</div>
                <div class="format-options">
                  <label 
                    v-for="format in exportFormats" 
                    :key="format.id"
                    class="format-option"
                    :class="{ active: selectedExportFormat === format.id }"
                    @click="selectedExportFormat = format.id"
                  >
                    <div class="format-icon">{{ format.icon }}</div>
                    <div class="format-info">
                      <div class="format-name">{{ format.name }}</div>
                      <div class="format-desc">{{ format.description }}</div>
                    </div>
                    <div class="format-check">
                      <span class="check-circle" :class="{ checked: selectedExportFormat === format.id }"></span>
                    </div>
                  </label>
                </div>
              </div>

              <!-- 导出选项 -->
              <div class="export-options-section">
                <div class="section-title">导出选项</div>
                
                <label class="option-item">
                  <input type="checkbox" v-model="exportOptions.includeImages" />
                  <span class="option-text">包含原始图片文件</span>
                </label>

                <label class="option-item">
                  <input type="checkbox" v-model="exportOptions.includeYaml" />
                  <span class="option-text">生成数据集配置文件 (data.yaml)</span>
                </label>

                <label class="option-item" v-if="selectedExportFormat === 'yolo'">
                  <input type="checkbox" v-model="exportOptions.normalizeCoordinates" />
                  <span class="option-text">归一化坐标 (YOLO标准格式)</span>
                </label>

                <label class="option-item">
                  <input type="checkbox" v-model="exportOptions.splitDataset" />
                  <span class="option-text">自动划分训练/验证/测试集</span>
                </label>

                <div v-if="exportOptions.splitDataset" class="split-ratio-inputs">
                  <div class="ratio-item">
                    <label>训练集</label>
                    <input type="number" v-model.number="exportOptions.trainRatio" min="0" max="1" step="0.1" />
                    <span>%</span>
                  </div>
                  <div class="ratio-item">
                    <label>验证集</label>
                    <input type="number" v-model.number="exportOptions.valRatio" min="0" max="1" step="0.1" />
                    <span>%</span>
                  </div>
                  <div class="ratio-item">
                    <label>测试集</label>
                    <input type="number" v-model.number="exportOptions.testRatio" min="0" max="1" step="0.1" />
                    <span>%</span>
                  </div>
                </div>
              </div>

              <!-- 类别映射 -->
              <div class="class-mapping-section">
                <div class="section-title">类别映射</div>
                <div class="class-mapping-hint">系统将自动检测标注中的类别并生成映射表</div>
                <div v-if="detectedClasses.length > 0" class="detected-classes">
                  <div v-for="(cls, idx) in detectedClasses" :key="cls" class="class-item">
                    <span class="class-id">{{ idx }}</span>
                    <span class="class-name">{{ cls }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="dialog-footer export-footer">
              <button class="dialog-btn secondary" type="button" @click="closeExportDialog">
                取消
              </button>
              <button 
                class="dialog-btn primary export-btn" 
                type="button" 
                @click="confirmExport"
                :disabled="isExporting"
              >
                <span v-if="isExporting">⏳ 正在打包...</span>
                <span v-else>📥 确认导出</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
</template>

<script setup>
import { computed, reactive, ref, onBeforeUnmount, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useIntersectionObserver } from '@vueuse/core'
import CreateBoardCard from '@/views/project/CreateBoardCard.vue'
import TeamCollaborationActions from '@/components/TeamCollaborationActions.vue'
import PendingReviewDialog from '@/components/PendingReviewDialog.vue'
import {
  createProject,
  listProjects,
  listProjectFiles,
  uploadProjectFile,
  getProjectFileDownloadUrl,
  deleteProjectApi,
  acceptSharedProject,
  createAnnotationSession,
  getFolderTasks,
  getTaskByFileId,
} from '@/api/projectStorage'
import { useUserStore } from '@/stores/user'
import JSZip from 'jszip' // 需要安装: npm install jszip
import { saveAs } from 'file-saver' // 需要安装: npm install file-saver


// ============ 基础状态 ============

const projectList = ref([])
const hoveredProjectId = ref(null)

const currentProjectId = ref(null)
const currentFolderId = ref(null)
const openedProjectMenuId = ref(null)

const searchKeyword = ref('')
const teamSearchKeyword = ref('')
const sortType = ref('created_desc')

const renameVisible = ref(false)
const renameProjectId = ref(null)
const renameValue = ref('')

const previewVisible = ref(false)
const previewImageUrl = ref('')
const previewFileName = ref('')

const workVisible = ref(false)
const currentWorkFileId = ref(null)
const workForm = reactive({
  mode: 'keyword',
  selectedTagIds: [],
   confidenceThreshold: 0.25, 
})
const selectedFileIds = ref([])

const deletingProjectId = ref(null)

const userStore = useUserStore()
const router = useRouter()
const previewUrlMap = new Map()
const progressSocket = ref(null)
const progressSocketStopped = ref(false)

// ============ 大图标注预览相关 ============

const previewImageRef = ref(null)
const imageWrapperRef = ref(null)
const previewMaskRef = ref(null)

const annotationPreviewVisible = ref(false)
const annotationPreviewImageUrl = ref('')
const annotationPreviewFileName = ref('')
const currentAnnotations = ref([])
const annotationImageLoaded = ref(false)
const annotationImageNaturalWidth = ref(0)
const annotationImageNaturalHeight = ref(0)
const currentPreviewTask = ref(null)
const currentPreviewIndex = ref(0)
const previewableFiles = ref([])
const annotationDataSource = ref('')
const pendingReviewVisible = ref(false)
const pendingReviewItems = ref([])

const touchStartX = ref(0)
const touchEndX = ref(0)
const containerSize = ref({ width: 0, height: 0 })
const imageRenderRect = ref({
  width: 0,
  height: 0,
  left: 0,
  top: 0,
})

// ============ 任务列表状态 ============

const labelingTasks = ref([])
const doneTasks = ref([])

// ============ 场景标签配置 ============

const scenes = ref([
  {
    id: 1,
    name: '场景1',
    tags: [
      { id: 1, name: 'person', color: '#d9c2f2' },
      { id: 2, name: 'car', color: '#f4b4af' },
      { id: 3, name: 'dog', color: '#b8c9f6' },
      { id: 4, name: 'cat', color: '#ecd68d' },
      { id: 5, name: 'cow', color: '#a9cf96' },
    ],
  },
  {
    id: 2,
    name: '场景2',
    tags: [
      { id: 6, name: 'horse', color: '#aee9ec' },
      { id: 7, name: 'tag2', color: '#f2d562' },
      { id: 8, name: 'tag3', color: '#eea2ca' },
    ],
  },
])


// ============ 数据导出相关状态 ============
const exportVisible = ref(false)
const selectedExportFormat = ref('yolo')
const isExporting = ref(false)
const detectedClasses = ref([])

// 导出格式配置
const exportFormats = [
  {
    id: 'yolo',
    name: 'YOLO 格式',
    icon: '📄',
    description: 'TXT文件，每行: <class_id> <x_center> <y_center> <width> <height>',
    extension: 'txt'
  },
  {
    id: 'coco',
    name: 'COCO JSON',
    icon: '📋',
    description: '单个JSON文件，包含所有图像和标注信息',
    extension: 'json'
  },
  {
    id: 'voc',
    name: 'PASCAL VOC',
    icon: '📑',
    description: 'XML文件，每图一个标注文件',
    extension: 'xml'
  }
]

// 导出选项
const exportOptions = reactive({
  includeImages: true,
  includeYaml: true,
  normalizeCoordinates: true,
  splitDataset: false,
  trainRatio: 0.7,
  valRatio: 0.2,
  testRatio: 0.1
})

// 待导出的文件列表（优先使用选中的，否则使用全部）
const selectedFilesForExport = computed(() => {
  if (selectedFileIds.value.length > 0) {
    return currentFolder.value?.files.filter(f => selectedFileIds.value.includes(f.id)) || []
  }
  return currentFolder.value?.files || []
})

// ============ 数据导出方法 ============

const openExportDialog = async () => {
  exportVisible.value = true
  selectedExportFormat.value = 'yolo'
  isExporting.value = false
  
  // 自动检测类别
  await detectClasses()
}

const closeExportDialog = () => {
  exportVisible.value = false
  isExporting.value = false
}

// 检测所有标注中的类别
const detectClasses = async () => {
  const classes = new Set()
  const files = selectedFilesForExport.value
  
  for (const file of files) {
    try {
      const task = await getTaskByFileId(currentProject.value.id, file.id)
      if (task?.task?.annotations) {
        task.task.annotations.forEach(anno => {
          const label = anno.label || anno.category || 'unknown'
          classes.add(label)
        })
      }
    } catch (e) {
      console.log('获取任务失败:', file.id)
    }
  }
  
  detectedClasses.value = Array.from(classes).sort()
}

// 确认导出
const confirmExport = async () => {
  if (selectedFilesForExport.value.length === 0) {
    window.alert('没有可导出的文件')
    return
  }

  isExporting.value = true
  
  try {
    const zip = new JSZip()
    const format = selectedExportFormat.value
    const files = selectedFilesForExport.value
    
    // 根据格式导出
    switch (format) {
      case 'yolo':
        await exportYOLOFormat(zip, files)
        break
      case 'coco':
        await exportCOCOFormat(zip, files)
        break
      case 'voc':
        await exportVOCFormat(zip, files)
        break
    }
    
    // 生成并下载zip文件
    const content = await zip.generateAsync({ type: 'blob' })
    const projectName = currentProject.value?.projectName || 'project'
    const timestamp = new Date().toISOString().slice(0, 10)
    saveAs(content, `${projectName}_annotations_${format}_${timestamp}.zip`)
    
    closeExportDialog()
  } catch (error) {
    console.error('导出失败:', error)
    window.alert('导出失败: ' + error.message)
  } finally {
    isExporting.value = false
  }
}

// YOLO格式导出
const exportYOLOFormat = async (zip, files) => {
  const labelsFolder = zip.folder('labels')
  const imagesFolder = zip.folder('images')
  const classMap = {}
  
  // 构建类别映射
  detectedClasses.value.forEach((cls, idx) => {
    classMap[cls] = idx
  })
  
  // 处理每个文件
  for (const file of files) {
    try {
      const taskData = await getTaskByFileId(currentProject.value.id, file.id)
      if (!taskData?.task?.annotations) continue
      
      const annotations = taskData.task.annotations
      const baseName = file.name.replace(/\.[^/.]+$/, '')
      
      // 生成YOLO格式标注
      const yoloLines = annotations.map(anno => {
        const label = anno.label || anno.category || 'unknown'
        const classId = classMap[label] || 0
        
        let x, y, w, h
        
        if (exportOptions.normalizeCoordinates) {
          // 归一化坐标 (YOLO标准)
          const imgWidth = anno.image_width || 1920
          const imgHeight = anno.image_height || 1080
          x = (anno.x + anno.width / 2) / imgWidth
          y = (anno.y + anno.height / 2) / imgHeight
          w = anno.width / imgWidth
          h = anno.height / imgHeight
        } else {
          // 绝对坐标
          x = anno.x + anno.width / 2
          y = anno.y + anno.height / 2
          w = anno.width
          h = anno.height
        }
        
        return `${classId} ${x.toFixed(6)} ${y.toFixed(6)} ${w.toFixed(6)} ${h.toFixed(6)}`
      })
      
      // 保存标注文件
      labelsFolder.file(`${baseName}.txt`, yoloLines.join('\n'))
      
      // 下载并保存图片
      if (exportOptions.includeImages) {
        try {
          const imageBlob = await fetchImageBlob(file.downloadUrl || file.previewUrl)
          const ext = file.name.split('.').pop()
          imagesFolder.file(`${baseName}.${ext}`, imageBlob)
        } catch (e) {
          console.log('下载图片失败:', file.name)
        }
      }
    } catch (e) {
      console.log('处理文件失败:', file.name, e)
    }
  }
  
  // 生成data.yaml
  if (exportOptions.includeYaml) {
    const yamlContent = generateDataYaml(detectedClasses.value)
    zip.file('data.yaml', yamlContent)
  }
  
  // 生成类别映射文件
  const classNamesContent = detectedClasses.value.map((cls, idx) => `${idx}: ${cls}`).join('\n')
  zip.file('classes.txt', classNamesContent)
}

// COCO格式导出
const exportCOCOFormat = async (zip, files) => {
  const cocoData = {
    info: {
      description: `${currentProject.value?.projectName || 'Project'} Annotations`,
      version: '1.0',
      year: new Date().getFullYear(),
      contributor: 'Annotation Platform',
      date_created: new Date().toISOString()
    },
    licenses: [{ id: 1, name: 'Unknown', url: '' }],
    images: [],
    annotations: [],
    categories: detectedClasses.value.map((cls, idx) => ({
      id: idx,
      name: cls,
      supercategory: 'object'
    }))
  }
  
  let annotationId = 1
  const classMap = {}
  detectedClasses.value.forEach((cls, idx) => {
    classMap[cls] = idx
  })
  
  const imagesFolder = zip.folder('images')
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    try {
      const taskData = await getTaskByFileId(currentProject.value.id, file.id)
      if (!taskData?.task?.annotations) continue
      
      const annotations = taskData.task.annotations
      const imageId = i + 1
      
      // 添加图像信息
      cocoData.images.push({
        id: imageId,
        file_name: file.name,
        height: annotations[0]?.image_height || 1080,
        width: annotations[0]?.image_width || 1920,
        date_captured: new Date().toISOString()
      })
      
      // 添加标注信息
      annotations.forEach(anno => {
        const label = anno.label || anno.category || 'unknown'
        const categoryId = classMap[label] || 0
        
        cocoData.annotations.push({
          id: annotationId++,
          image_id: imageId,
          category_id: categoryId,
          bbox: [anno.x, anno.y, anno.width, anno.height],
          area: anno.width * anno.height,
          segmentation: [],
          iscrowd: 0
        })
      })
      
      // 下载图片
      if (exportOptions.includeImages) {
        try {
          const imageBlob = await fetchImageBlob(file.downloadUrl || file.previewUrl)
          const ext = file.name.split('.').pop()
          imagesFolder.file(file.name, imageBlob)
        } catch (e) {
          console.log('下载图片失败:', file.name)
        }
      }
    } catch (e) {
      console.log('处理文件失败:', file.name)
    }
  }
  
  // 保存COCO JSON
  zip.file('annotations.json', JSON.stringify(cocoData, null, 2))
}

// PASCAL VOC格式导出
const exportVOCFormat = async (zip, files) => {
  const annotationsFolder = zip.folder('Annotations')
  const imagesFolder = zip.folder('JPEGImages')
  
  for (const file of files) {
    try {
      const taskData = await getTaskByFileId(currentProject.value.id, file.id)
      if (!taskData?.task?.annotations) continue
      
      const annotations = taskData.task.annotations
      const baseName = file.name.replace(/\.[^/.]+$/, '')
      const imgWidth = annotations[0]?.image_width || 1920
      const imgHeight = annotations[0]?.image_height || 1080
      
      // 生成VOC XML
      const xmlContent = generateVOCXml(baseName, imgWidth, imgHeight, annotations)
      annotationsFolder.file(`${baseName}.xml`, xmlContent)
      
      // 下载图片
      if (exportOptions.includeImages) {
        try {
          const imageBlob = await fetchImageBlob(file.downloadUrl || file.previewUrl)
          const ext = file.name.split('.').pop()
          imagesFolder.file(`${baseName}.${ext}`, imageBlob)
        } catch (e) {
          console.log('下载图片失败:', file.name)
        }
      }
    } catch (e) {
      console.log('处理文件失败:', file.name)
    }
  }
}

// 辅助函数：获取图片Blob
const fetchImageBlob = async (url) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error('Failed to fetch image')
  return await response.blob()
}

// 生成YOLO data.yaml
const generateDataYaml = (classes) => {
  return `path: ./dataset
train: images/train
val: images/val
test: images/test

nc: ${classes.length}
names: [${classes.map(c => `'${c}'`).join(', ')}]
`
}

// 生成VOC XML
const generateVOCXml = (filename, width, height, annotations) => {
  const objects = annotations.map(anno => {
    const label = anno.label || anno.category || 'unknown'
    return `
  <object>
    <name>${label}</name>
    <pose>Unspecified</pose>
    <truncated>0</truncated>
    <difficult>0</difficult>
    <bndbox>
      <xmin>${Math.round(anno.x)}</xmin>
      <ymin>${Math.round(anno.y)}</ymin>
      <xmax>${Math.round(anno.x + anno.width)}</xmax>
      <ymax>${Math.round(anno.y + anno.height)}</ymax>
    </bndbox>
  </object>`
  }).join('')
  
  return `<?xml version="1.0" encoding="UTF-8"?>
<annotation>
  <folder>VOC2007</folder>
  <filename>${filename}</filename>
  <source>
    <database>The VOC2007 Database</database>
    <annotation>PASCAL VOC2007</annotation>
  </source>
  <size>
    <width>${width}</width>
    <height>${height}</height>
    <depth>3</depth>
  </size>
  <segmented>0</segmented>${objects}
</annotation>`
}

// ============ 计算属性 ============

const currentProject = computed(
  () => projectList.value.find((item) => item.id === currentProjectId.value) || null
)
const currentUserId = computed(() => userStore.user?.id || '')

const currentFolder = computed(() => {
  if (!currentProject.value || !currentFolderId.value) return null
  return currentProject.value.folders.find((item) => item.id === currentFolderId.value) || null
})

const currentWorkFile = computed(() => {
  if (!currentProject.value || !currentWorkFileId.value) return null

  for (const folder of currentProject.value.folders || []) {
    const matched = (folder.files || []).find((file) => file.id === currentWorkFileId.value)
    if (matched) return matched
  }

  return null
})

const selectedFiles = computed(() => {
  if (!currentFolder.value) return []
  return currentFolder.value.files.filter((file) => selectedFileIds.value.includes(file.id))
})

const workSummaryText = computed(() => {
  if (selectedFiles.value.length > 1) return `已选择 ${selectedFiles.value.length} 个文件`
  return `当前文件：${currentWorkFile.value?.name || ''}`
})

const allTags = computed(() => scenes.value.flatMap((scene) => scene.tags))

const workSelectedTags = computed(() =>
  allTags.value.filter((tag) => workForm.selectedTagIds.includes(tag.id))
)

const filteredProjectList = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const teamKeyword = teamSearchKeyword.value.trim().toLowerCase()
  let list = [...projectList.value]

  if (keyword) {
    list = list.filter((project) => project.projectName.trim().toLowerCase().includes(keyword))
  }
  if (teamKeyword) {
    list = list.filter((project) =>
      (project.organizationNickname || '').trim().toLowerCase().includes(teamKeyword)
    )
  }

  list.sort((a, b) => {
    if (a.isSharedCopy && !b.isSharedCopy) return -1
    if (!a.isSharedCopy && b.isSharedCopy) return 1
    if (a.isSharedCopy && b.isSharedCopy) return Number(b.sharedAt || 0) - Number(a.sharedAt || 0)
    return 0
  })

  const comparePinned = (a, b) => {
    const aPendingShared = Boolean(a.isSharedCopy && !a.shareAcceptedAt)
    const bPendingShared = Boolean(b.isSharedCopy && !b.shareAcceptedAt)
    if (aPendingShared && !bPendingShared) return -1
    if (!aPendingShared && bPendingShared) return 1
    return 0
  }

  if (sortType.value === 'created_desc') {
    list.sort((a, b) => comparePinned(a, b) || Number(b.createdAt || 0) - Number(a.createdAt || 0))
  } else if (sortType.value === 'created_asc') {
    list.sort((a, b) => comparePinned(a, b) || Number(a.createdAt || 0) - Number(b.createdAt || 0))
  } else if (sortType.value === 'name_asc') {
    list.sort((a, b) => comparePinned(a, b) || a.projectName.localeCompare(b.projectName, 'zh-CN'))
  } else if (sortType.value === 'name_desc') {
    list.sort((a, b) => comparePinned(a, b) || b.projectName.localeCompare(a.projectName, 'zh-CN'))
  }

  return list
})
// ============ 优化：缓存选择状态检查 ============

// 使用 Set 优化查找性能 O(n) -> O(1)
const selectedFileIdSet = computed(() => new Set(selectedFileIds.value))

const isFileSelected = (fileId) => selectedFileIdSet.value.has(fileId)

// 优化：文件状态映射缓存
const fileStatusMap = computed(() => {
  const map = new Map()
  currentFolder.value?.files.forEach(file => {
    map.set(file.id, file.status)
  })
  return map
})
const renameError = computed(() => {
  if (!renameVisible.value) return ''

  const name = renameValue.value.trim()
  if (!name) return '请输入项目名'

  const exists = projectList.value.some((project) => {
    if (project.id === renameProjectId.value) return false
    return project.projectName.trim().toLowerCase() === name.toLowerCase()
  })

  if (exists) return '项目名已存在，请更换一个名称'
  return ''
})

const isPendingFolder = computed(() => currentFolder.value?.name === '待标注')
const isLabelingFolder = computed(() => currentFolder.value?.name === '标注中')
const isDoneFolder = computed(() => currentFolder.value?.name === '已标注')

const getWorkButtonText = computed(() => {
  if (isPendingFolder.value) return '工作'
  if (isLabelingFolder.value) return '继续'
  if (isDoneFolder.value) return '查看'
  return '工作'
})

const getEmptyFolderText = computed(() => {
  if (isPendingFolder.value) return '该文件夹暂无待标注文件'
  if (isLabelingFolder.value) return '该文件夹暂无标注中文件'
  if (isDoneFolder.value) return '该文件夹暂无已标注文件'
  return '该文件夹暂无文件'
})

const canGoPrev = computed(() => currentPreviewIndex.value > 0)
const canGoNext = computed(() => currentPreviewIndex.value < previewableFiles.value.length - 1)
const annotationLabels = computed(() => {
  const labels = currentAnnotations.value
    .map((anno) => (anno.label || '').trim())
    .filter((label) => Boolean(label))
  return [...new Set(labels)]
})
const isCurrentProjectReviewer = computed(
  () =>
    Boolean(currentProject.value?.reviewerId) &&
    currentProject.value?.reviewerId === currentUserId.value
)
const pendingReviewFiles = computed(() => {
  if (!currentProject.value) return []
  const doneFolder = currentProject.value.folders.find((folder) => folder.name === '已标注')
  return Array.isArray(doneFolder?.files) ? doneFolder.files : []
})
const pendingReviewCount = computed(() => pendingReviewFiles.value.length)
const showPendingReviewButton = computed(() => isCurrentProjectReviewer.value)

const imageContainerStyle = computed(() => {
  if (!annotationImageLoaded.value) {
    return {
      width: '100%',
      height: '100%',
    }
  }

  const imgWidth = annotationImageNaturalWidth.value
  const imgHeight = annotationImageNaturalHeight.value
  const imgRatio = imgWidth / imgHeight

  const availableWidth = containerSize.value.width || window.innerWidth * 0.9
  const availableHeight = containerSize.value.height || window.innerHeight - 120

  const containerRatio = availableWidth / availableHeight

  let finalWidth = 0
  let finalHeight = 0

  if (imgRatio > containerRatio) {
    finalWidth = availableWidth
    finalHeight = availableWidth / imgRatio
  } else {
    finalHeight = availableHeight
    finalWidth = availableHeight * imgRatio
  }

  return {
    width: `${finalWidth}px`,
    height: `${finalHeight}px`,
    position: 'relative',
  }
})

const svgOverlayStyle = computed(() => {
  if (!annotationImageLoaded.value) return {}

  return {
    position: 'absolute',
    left: `${imageRenderRect.value.left}px`,
    top: `${imageRenderRect.value.top}px`,
    width: `${imageRenderRect.value.width}px`,
    height: `${imageRenderRect.value.height}px`,
    pointerEvents: 'none',
  }
})

// ============ 工具函数 ============

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待标注',
    labeling: '标注中',
    done: '已完成',
  }
  return statusMap[status] || status
}

const getLabelWidth = (label) => {
  const text = String(label || '未命名')
  
  // 创建临时 canvas 测量文字宽度
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  // 匹配 SVG 中的字体设置
  ctx.font = '600 13px system-ui, -apple-system, sans-serif'
  
  const metrics = ctx.measureText(text)
  // 实际宽度 + 左右内边距(12px) + 小图标空间(4px)
  const width = Math.ceil(metrics.width) + 16
  
  // 限制最小和最大宽度
  return Math.max(50, Math.min(200, width))
}

const mapBackendFile = (backendFile) => {
  const mapped = {
    id: backendFile.id,
    name: backendFile.filename,
    status: backendFile.status || 'pending',
    relativePath: '',
    type: backendFile.mime_type || '',
    size: backendFile.size_bytes || 0,
    file: null,
    storageBackend: backendFile.storage_backend || 'supabase',
    downloadUrl: backendFile.download_url || getProjectFileDownloadUrl(backendFile.id),
    previewUrl:
      backendFile.preview_url ||
      backendFile.download_url ||
      getProjectFileDownloadUrl(backendFile.id),
  }

  return mapped
}
const getProjectPendingReviewCount = (project) => {
  const doneFolder = project?.folders?.find((folder) => folder.name === '已标注')
  return Array.isArray(doneFolder?.files) ? doneFolder.files.length : 0
}
const showProjectReviewDot = (project) =>
  project?.reviewerId === currentUserId.value && getProjectPendingReviewCount(project) > 0

// ============ 数据加载 ============

const loadProjects = async () => {
  console.log('[VUE-001] 开始加载项目列表')

  try {
    const owner = userStore.user?.username || 'default'
    const data = await listProjects(owner)

    console.log(`[VUE-002] 获取${data?.length || 0}个项目`)

    const projectData = await Promise.all(
      (data || []).map(async (project) => {
        const fileResp = await listProjectFiles(project.id)
        const allFiles = (fileResp || []).map(mapBackendFile)

        const pendingFiles = allFiles.filter((f) => f.status === 'pending')
        const labelingFiles = allFiles.filter((f) => f.status === 'labeling')
        const doneFiles = allFiles.filter((f) => f.status === 'done')

        console.log(
          `[VUE-003] 项目[${project.name}] | pending=${pendingFiles.length}, labeling=${labelingFiles.length}, done=${doneFiles.length}`
        )

        return {
          id: project.id,
          projectName: project.name,
          remark: project.description || '',
          mode: 'keyword',
          selectedTagIds: [],
          selectedTags: [],
          createdAt: new Date(project.created_at).getTime(),
          sharedAt: project.shared_at ? new Date(project.shared_at).getTime() : null,
          isSharedCopy: Boolean(project.is_shared_copy),
          sharedBy: project.shared_by || '',
          shareMessage: project.share_message || '',
          organizationNickname: project.organization_nickname || '',
          shareAcceptedAt: project.share_accepted_at
            ? new Date(project.share_accepted_at).getTime()
            : null,
          reviewerId: project.reviewer_id || '',
          folders: [
            { id: `pending_${project.id}`, name: '待标注', files: pendingFiles },
            { id: `labeling_${project.id}`, name: '标注中', files: labelingFiles },
            { id: `done_${project.id}`, name: '已标注', files: doneFiles },
          ],
        }
      })
    )

    projectList.value = [...projectData]
    console.log('[VUE-004] projectList已更新，长度=', projectList.value.length)

    await nextTick()
    console.log('[VUE-005] nextTick完成，DOM已更新')
  } catch (error) {
    console.error('读取项目失败：', error)
    window.alert(error?.response?.data?.detail || error.message || '读取项目失败')
  }
}

const loadFolderTasks = async () => {
  if (!currentProject.value) return

  try {
    if (isLabelingFolder.value) {
      console.log(`[LOAD] 加载标注中任务 | project_id=${currentProject.value.id}`)
      const data = await getFolderTasks(currentProject.value.id, 'labeling')

      if (data?.tasks) {
        // ⚠️ 关键修复：过滤掉 null/undefined 元素
        labelingTasks.value = data.tasks.filter(t => t && t.task_id && t.file_id)
        console.log(`[LOAD] 加载到 ${labelingTasks.value.length} 个有效标注中任务`)

        const labelingFolder = currentProject.value.folders.find((f) => f.name === '标注中')
        if (labelingFolder) {
          labelingFolder.files.forEach((file) => {
            const task = labelingTasks.value.find((t) => t.file_id === file.id)
            if (task) {
              file.taskId = task.task_id
              file.taskStatus = task.status
            }
          })
        }
      }
    } else if (isDoneFolder.value) {
      console.log(`[LOAD] 加载已完成任务 | project_id=${currentProject.value.id}`)
      const data = await getFolderTasks(currentProject.value.id, 'done')

      if (data?.tasks) {
        // ⚠️ 同样过滤 null 元素
        doneTasks.value = data.tasks.filter(t => t && t.task_id && t.file_id)
        console.log(`[LOAD] 加载到 ${doneTasks.value.length} 个有效已完成任务`)

        const doneFolder = currentProject.value.folders.find((f) => f.name === '已标注')
        if (doneFolder) {
          doneFolder.files.forEach((file) => {
            const task = doneTasks.value.find((t) => t.file_id === file.id)
            if (task) {
              file.taskId = task.task_id
            }
          })
        }
      }
    }
  } catch (error) {
    console.error('加载任务列表失败:', error)
    labelingTasks.value = []
    doneTasks.value = []
  }
}

// ============ 导航方法 ============

const handleCreateProject = async (projectData) => {
  console.log('CreateBoardCard 返回的 projectData =>', projectData)
  const owner_id = userStore.user?.username || 'default'

  try {
    const data = await createProject({
      name: projectData.projectName,
      description: projectData.remark || '',
      owner_id,
      organization_nickname: userStore.currentOrganization?.organization_nickname || undefined,
    })

    const folders = Array.isArray(projectData.folders) ? projectData.folders : []
    const pendingFolder = folders.find((folder) => folder.name === '待标注')
    const pendingFiles = Array.isArray(pendingFolder?.files) ? pendingFolder.files : []

    for (const item of pendingFiles) {
      if (item?.file) {
        await uploadProjectFile(data.id, item.file, owner_id)
      }
    }

    await loadProjects()
  } catch (error) {
    console.error('创建项目失败：', error)
    window.alert(error?.response?.data?.detail || error.message || '创建项目失败')
  }
}

const enterProject = async (project) => {
  closeProjectMenu()
  if (project.isSharedCopy && !project.shareAcceptedAt) {
    try {
      const resp = await acceptSharedProject(project.id)
      project.shareAcceptedAt = resp?.accepted_at
        ? new Date(resp.accepted_at).getTime()
        : Date.now()
    } catch (error) {
      window.alert(error?.response?.data?.detail || error?.message || '接收分享项目失败')
      return
    }
  }
  currentProjectId.value = project.id
  currentFolderId.value = null
}

const backToProjectList = () => {
  closeProjectMenu()
  currentProjectId.value = null
  currentFolderId.value = null
  selectedFileIds.value = []
  labelingTasks.value = []
  doneTasks.value = []
  closePendingReviewDialog()
}

const enterFolder = async (folder) => {
  currentFolderId.value = folder.id
  selectedFileIds.value = []
  await nextTick()
  await loadFolderTasks()
}

const backToFolderList = () => {
  currentFolderId.value = null
  selectedFileIds.value = []
  labelingTasks.value = []
  doneTasks.value = []
  closePendingReviewDialog()
}

// ============ 文件操作 ============

const showRemark = (id) => {
  hoveredProjectId.value = id
}

const hideRemark = () => {
  hoveredProjectId.value = null
}

const IMAGE_NAME_PATTERN = /\.(png|jpe?g|gif|bmp|webp|svg|tiff?)$/i
const isImageFile = (file) => {
  if (typeof file?.type === 'string' && file.type.startsWith('image/')) return true
  if (typeof file?.name === 'string' && IMAGE_NAME_PATTERN.test(file.name)) return true
  return false
}


const previewFile = (file) => {
  previewFileName.value = file.name || ''

  if (!isImageFile(file)) {
    const targetUrl = file.downloadUrl || getFilePreviewUrl(file)
    if (targetUrl) window.open(targetUrl, '_blank', 'noopener,noreferrer')
    return
  }

  const imageUrl = getFilePreviewUrl(file)
  if (!imageUrl) return

  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }

  previewImageUrl.value = imageUrl
  previewVisible.value = true
}

const handleImagePreview = (file) => {
  if (isDoneFolder.value || isLabelingFolder.value) {
    openAnnotationPreview(
      file,
      currentFolder.value?.files.findIndex((f) => f.id === file.id)
    )
    return
  }
  previewFile(file)
}

const closePreview = () => {
  previewVisible.value = false
  previewFileName.value = ''

  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }
  previewImageUrl.value = ''
}

// ============ 性能优化：懒加载与缓存 ============



// 缓存系统
const urlCache = new Map()           // URL 缓存
const imageLoadCache = new Set()     // 已加载图片记录
const preloadQueue = new Set()       // 预加载队列

// 自定义懒加载指令
const vLazy = {
  mounted(el, binding) {
    const src = binding.value
    if (!src) return
    
    // 设置占位符
    el.style.opacity = '0'
    el.style.transition = 'opacity 0.3s'
    
    const { stop } = useIntersectionObserver(
      el,
      ([{ isIntersecting }]) => {
        if (isIntersecting) {
          // 开始加载
          el.src = src
          el.onload = () => {
            el.style.opacity = '1'
            imageLoadCache.add(el.dataset.fileId)
          }
          el.onerror = () => {
            el.style.opacity = '1'
            el.src = '' // 显示错误占位
          }
          stop()
        }
      },
      { 
        rootMargin: '100px',  // 提前 100px 开始加载
        threshold: 0.01 
      }
    )
    
    el._stopObserver = stop
  },
  unmounted(el) {
    el._stopObserver?.()
  }
}

// 优化后的获取预览 URL（带缓存）
const getFilePreviewUrl = (file) => {
  if (!isImageFile(file)) return ''
  
  const cacheKey = file.id
  if (urlCache.has(cacheKey)) {
    return urlCache.get(cacheKey)
  }
  
  let url = ''
  if (file.file) {
    if (!previewUrlMap.has(file.id)) {
      const objectUrl = URL.createObjectURL(file.file)
      previewUrlMap.set(file.id, objectUrl)
    }
    url = previewUrlMap.get(file.id)
  } else {
    url = file.previewUrl || file.downloadUrl || ''
  }
  
  // 只缓存非 blob URL（blob URL 需要手动管理生命周期）
  if (!url.startsWith('blob:')) {
    urlCache.set(cacheKey, url)
  }
  
  return url
}

// 预加载下一张图片（用于预览弹窗）
const preloadNextImage = (currentIndex) => {
  const nextIndex = currentIndex + 1
  if (nextIndex >= previewableFiles.value.length) return
  
  const nextFile = previewableFiles.value[nextIndex]
  if (!nextFile || preloadQueue.has(nextFile.id)) return
  
  preloadQueue.add(nextFile.id)
  const img = new Image()
  img.onload = () => imageLoadCache.add(nextFile.id)
  img.src = getFilePreviewUrl(nextFile)
}

// 批量预加载（当前视口附近的图片）
const batchPreload = (centerIndex, range = 3) => {
  const files = previewableFiles.value
  for (let i = centerIndex - range; i <= centerIndex + range; i++) {
    if (i >= 0 && i < files.length && i !== centerIndex) {
      preloadNextImage(i - 1)
    }
  }
}

// ============ 标注预览 ============

const getPreviewableFiles = () => {
  if (!currentFolder.value) return []
  return currentFolder.value.files.filter((file) => isImageFile(file))
}

const loadDraftFromStorage = async (fileId) => {
  const key = `annotation_draft_${currentProject.value?.id}_${fileId}`
  const draft = localStorage.getItem(key)
  return draft ? JSON.parse(draft) : null
}

const loadPreviewData = async (file) => {
  annotationPreviewFileName.value = file.name || ''
  annotationPreviewImageUrl.value = getFilePreviewUrl(file) || file.downloadUrl || ''
  annotationImageLoaded.value = false
  annotationDataSource.value = ''
  
  currentPreviewTask.value = null

  let annotations = []
  let taskData = null

  try {
    const draftData = await loadDraftFromStorage(file.id)
    if (draftData?.annotations?.length > 0) {
      annotations = draftData.annotations
      annotationDataSource.value = '草稿'
    }
  } catch (e) {
    console.log('草稿表查询失败:', e)
  }

  // 标注中文件夹：优先从 labelingTasks 中查找（使用过滤后的列表）
  if (isLabelingFolder.value) {
    const validTasks = labelingTasks.value.filter(t => t && t.file_id)
    taskData = validTasks.find((t) => t.file_id === file.id)
    if (taskData?.annotations?.length > 0) {
      annotations = taskData.annotations
      annotationDataSource.value = '任务'
    }
  } else if (isDoneFolder.value) {
    const validTasks = doneTasks.value.filter(t => t && t.file_id)
    taskData = validTasks.find((t) => t.file_id === file.id)
    if (taskData?.annotations?.length > 0) {
      annotations = taskData.annotations
      annotationDataSource.value = '任务'
    }
  }

  // 如果没有找到 taskData，主动从后端获取
  if (!taskData) {
    try {
      console.log(`[PREVIEW] 从后端加载任务 | file_id=${file.id}`)
      const data = await getTaskByFileId(currentProject.value.id, file.id)
      if (data?.task) {
        taskData = data.task
        if (data.task.annotations?.length > 0) {
          annotations = data.task.annotations
          annotationDataSource.value = '任务(后端)'
        } else if (data.task.pre_annotations?.length > 0) {
          annotations = data.task.pre_annotations
          annotationDataSource.value = '预标注'
        }
      }
    } catch (e) {
      console.log('后端查询失败:', e)
    }
  }

  // 其他本地缓存查找逻辑...
  if (annotations.length === 0) {
    const keys = [
      `annotation_draft_${currentProject.value?.id}_${file.id}`,
      `draft_${file.id}`,
      `pre_annotations_${taskData?.task_id}`,
    ]

    for (const key of keys) {
      const data = localStorage.getItem(key)
      if (data) {
        try {
          const parsed = JSON.parse(data)
          if (parsed.annotations?.length > 0) {
            annotations = parsed.annotations
            annotationDataSource.value = '本地缓存'
            break
          }
        } catch (e) {
          // ignore
        }
      }
    }
  }

  // ========== 关键修复：保留颜色信息 ==========
currentAnnotations.value = annotations.map((anno) => ({
  x: anno.x || anno.bbox?.[0] || 0,
  y: anno.y || anno.bbox?.[1] || 0,
  width: anno.width || anno.bbox?.[2] || 0,
  height: anno.height || anno.bbox?.[3] || 0,
  label: anno.label || anno.category || anno.name || '未命名',
 color: getLabelColor(anno.label || anno.category || anno.name), // 优先使用标注自带的颜色
}))


  currentPreviewTask.value = taskData

  if (currentAnnotations.value.length === 0) {
    console.log(`[PREVIEW] 未找到标注数据 | file_id=${file.id}`)
  }
  
  if (!taskData && isLabelingFolder.value) {
    console.warn(`[PREVIEW] 警告：标注中文件夹的文件没有对应的 task | file_id=${file.id}`)
  }
}
const getLabelColor = (label) => {
  if (!label) return '#ff0000'
  
  // 与标注页面 useColorManager 保持一致的颜色映射
  const CATEGORY_COLORS = {
    // 人物 - 红色系
    'person': '#ff0000', 'people': '#ff0000', 'man': '#ff0000',
    'woman': '#ff0000', 'child': '#ff4444', 'pedestrian': '#ff0000',
    
    // 交通工具 - 蓝色系  
    'vehicle': '#0000ff', 'car': '#0000ff', 'truck': '#0000ff',
    'bus': '#0000ff', 'motorcycle': '#0000ff', 'bicycle': '#0000ff',
    'van': '#0000ff', 'suv': '#0000ff', 'trailer': '#0000ff',
    
    // 动物 - 绿色系
    'animal': '#00ff00', 'dog': '#00ff00', 'cat': '#00ff00',
    'bird': '#00ff00', 'horse': '#00ff00', 'sheep': '#00ff00',
    'cow': '#00ff00', 'zebra': '#ffeb3b', 'giraffe': '#ff9800',
    'elephant': '#8b4513', 'bear': '#8b4513', 'panda': '#ff69b4',
    
    // 其他常见标签（与 useColorManager 一致）
    'traffic light': '#ffff00', 'stop sign': '#ff8800',
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
    'cake': '#ffb6c1',
  }

  const lowerLabel = label.toLowerCase()
  
  // 精确匹配
  if (CATEGORY_COLORS[lowerLabel]) {
    return CATEGORY_COLORS[lowerLabel]
  }
  
  // 包含匹配（如 "red car" 包含 "car"）
  for (const [keyword, color] of Object.entries(CATEGORY_COLORS)) {
    if (lowerLabel.includes(keyword)) {
      return color
    }
  }
  
  // 回退：使用与 useColorManager 一致的哈希生成
  const usedColors = Object.values(CATEGORY_COLORS)
  const COLOR_POOL = [
    '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff',
    '#00ffff', '#ff8800', '#8800ff', '#88ff00', '#ff0088',
    '#0088ff', '#888888', '#ffaa00', '#aa00ff', '#aaff00',
    '#ff6600', '#6600ff', '#00ff66', '#ff0066', '#66ff00'
  ]
  
  const availableColors = COLOR_POOL.filter(c => !usedColors.includes(c))
  
  if (availableColors.length > 0) {
    const hash = label.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    return availableColors[Math.abs(hash) % availableColors.length]
  }
  
  return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')
}

// 判断标签是否应该显示在框下方（避免顶部溢出）
const isLabelBelow = (anno) => {
  // 如果标注框在图片顶部 30px 以内，标签显示在下方
  return anno.y < 30
}

// 获取标签样式（智能定位，避免溢出）
const getLabelStyle = (anno) => {
  const isBelow = isLabelBelow(anno)
  
  // 计算水平位置，避免左右溢出
  let leftPercent = (anno.x / annotationImageNaturalWidth.value) * 100
  
  // 限制在 2-98% 范围内，避免贴边
  leftPercent = Math.max(2, Math.min(98, leftPercent))
  
  // 计算垂直位置
  let topPercent
  if (isBelow) {
    // 显示在框下方：框底部 + 4px 偏移
    topPercent = ((anno.y + anno.height + 4) / annotationImageNaturalHeight.value) * 100
  } else {
    // 显示在框上方（原逻辑）：框顶部 - 4px
    topPercent = (Math.max(0, anno.y - 4) / annotationImageNaturalHeight.value) * 100
  }
  
  return {
    left: `${leftPercent}%`,
    top: `${topPercent}%`,
    backgroundColor: anno.color || '#ff0000',
    transform: isBelow ? 'translateY(0)' : 'translateY(-100%)'
  }
}

const openAnnotationPreview = async (file, index = null) => {
  try {
    previewableFiles.value = getPreviewableFiles()
    currentPreviewIndex.value =
      index !== null ? index : previewableFiles.value.findIndex((f) => f.id === file.id)

    if (currentPreviewIndex.value === -1) currentPreviewIndex.value = 0

    updateContainerSize()
    
    // 先加载当前图片
    await loadPreviewData(previewableFiles.value[currentPreviewIndex.value])
    
    annotationPreviewVisible.value = true

    // 预加载相邻图片（关键优化）
    nextTick(() => {
      batchPreload(currentPreviewIndex.value, 2)
      previewMaskRef.value?.focus()
    })
  } catch (error) {
    console.error('打开大图预览失败:', error)
    window.alert('加载标注预览失败')
  }
}
const closeAnnotationPreview = () => {
  annotationPreviewVisible.value = false
  annotationPreviewImageUrl.value = ''
  annotationPreviewFileName.value = ''
  currentAnnotations.value = []
  annotationImageLoaded.value = false
  annotationImageNaturalWidth.value = 0
  annotationImageNaturalHeight.value = 0
  currentPreviewTask.value = null
  currentPreviewIndex.value = 0
  previewableFiles.value = []
  annotationDataSource.value = ''
}

const updateContainerSize = () => {
  const vw = window.innerWidth
  const vh = window.innerHeight

  containerSize.value = {
    width: vw * 0.9 - 48,
    height: vh - 120,
  }
}

const updateImageRenderRect = () => {
  const img = previewImageRef.value
  const wrapper = imageWrapperRef.value
  if (!img || !wrapper) return

  const wrapperRect = wrapper.getBoundingClientRect()
  const imgRect = img.getBoundingClientRect()

  imageRenderRect.value = {
    width: imgRect.width,
    height: imgRect.height,
    left: imgRect.left - wrapperRect.left,
    top: imgRect.top - wrapperRect.top,
  }
}

const onAnnotationImageLoad = (event) => {
  const img = event.target
  annotationImageNaturalWidth.value = img.naturalWidth
  annotationImageNaturalHeight.value = img.naturalHeight
  annotationImageLoaded.value = true
  nextTick(() => updateImageRenderRect())
}

const goToPrevImage = async () => {
  if (!canGoPrev.value) return
  currentPreviewIndex.value--
  annotationImageLoaded.value = false
  await loadPreviewData(previewableFiles.value[currentPreviewIndex.value])
}

const goToNextImage = async () => {
  if (!canGoNext.value) return
  currentPreviewIndex.value++
  annotationImageLoaded.value = false
  await loadPreviewData(previewableFiles.value[currentPreviewIndex.value])
}

const handlePreviewKeydown = (e) => {
  if (e.key === 'ArrowLeft') goToPrevImage()
  else if (e.key === 'ArrowRight') goToNextImage()
  else if (e.key === 'Escape') closeAnnotationPreview()
}

const handleTouchStart = (e) => {
  touchStartX.value = e.touches[0].clientX
}

const handleTouchMove = (e) => {
  touchEndX.value = e.touches[0].clientX
}

const handleTouchEnd = (e) => {
  touchEndX.value = e.changedTouches[0].clientX
  const distance = touchEndX.value - touchStartX.value

  if (Math.abs(distance) > 50) {
    if (distance > 0) goToPrevImage()
    else goToNextImage()
  }
}

const continueFromPreview = () => {
  // 立即捕获当前值，避免竞态条件
  const task = currentPreviewTask.value
  
  if (!task?.task_id) {
    console.error('[CONTINUE] 无法继续标注：task 为空或缺少 task_id', task)
    window.alert('无法继续标注：任务信息加载中或不存在，请稍后再试')
    return
  }
  
  // 使用捕获的 task 继续后续逻辑...
  const validLabelingTasks = labelingTasks.value.filter(t => t && t.task_id)
  
  if (validLabelingTasks.length === 0) {
    console.error('[CONTINUE] 无法继续标注：没有有效的标注任务')
    window.alert('无法继续标注：标注任务列表为空，请刷新页面重试')
    return
  }
  
  const taskExists = validLabelingTasks.some(t => t.task_id === task.task_id)
  if (!taskExists) {
    validLabelingTasks.push(task)
  }
  
  closeAnnotationPreview()
  navigateToAnnotate(task, validLabelingTasks)  // 使用捕获的 task
}

const handleResize = () => {
  if (annotationPreviewVisible.value) {
    updateContainerSize()
    nextTick(() => updateImageRenderRect())
  }
}

// ============ 工作流核心方法 ============

const handleWork = async (file) => {
  if (!currentProject.value) return

  if (isPendingFolder.value) {
    selectedFileIds.value = [file.id]
    currentWorkFileId.value = file.id
    workForm.mode = currentProject.value.mode || 'keyword'
    workForm.selectedTagIds = []
    workVisible.value = true
  } else if (isLabelingFolder.value) {
    await loadSingleFileTask(file)
  } else if (isDoneFolder.value) {
    await openAnnotationPreview(file)
  }
}

const loadSingleFileTask = async (file) => {
  try {
    console.log(`[WORK] 加载单个文件任务 | file_id=${file.id}`)

    // 使用过滤后的列表
    const validLabelingTasks = labelingTasks.value.filter(t => t && t.file_id)
    const cachedTask = validLabelingTasks.find((t) => t.file_id === file.id)
    
    if (cachedTask) {
      console.log(`[WORK] 从缓存找到任务 | task_id=${cachedTask.task_id}`)
      navigateToAnnotate(cachedTask, validLabelingTasks)
      return
    }

    const data = await getTaskByFileId(currentProject.value.id, file.id)
    if (data?.task) {
      console.log(`[WORK] 从后端获取任务 | task_id=${data.task.task_id}`)
      navigateToAnnotate(data.task, [data.task].filter(t => t && t.task_id))
    } else {
      window.alert('该文件暂无标注任务，请先开始标注')
    }
  } catch (error) {
    console.error('加载任务失败:', error)
    window.alert('加载标注任务失败')
  }
}

const continueLabeling = () => {
  // 过滤 null 元素
  const validTasks = labelingTasks.value.filter(t => t && t.task_id)
  
  if (validTasks.length === 0) {
    window.alert('暂无标注中的任务')
    return
  }

  const firstTask = validTasks.find((t) => t.status === 'labeling') || validTasks[0]
  console.log(
    `[CONTINUE] 继续标注 | task_id=${firstTask.task_id}, total=${validTasks.length}`
  )

  navigateToAnnotate(firstTask, validTasks)
}
const reviewCompleted = () => {
  // 过滤 null 元素
  const validTasks = doneTasks.value.filter(t => t && t.task_id)
  
  if (validTasks.length === 0) {
    window.alert('暂无已标注的文件')
    return
  }

  const firstTask = validTasks[0]
  navigateToAnnotate(firstTask, validTasks)
}

const openPendingReviewDialog = async () => {
  if (!currentProject.value) return
  pendingReviewVisible.value = true
  pendingReviewItems.value = pendingReviewFiles.value.map((file) => ({
    ...file,
    previewUrl: getFilePreviewUrl(file) || file.downloadUrl || '',
    annotationCount: 0,
  }))

  const reviewItems = await Promise.all(
    pendingReviewFiles.value.map(async (file) => {
      try {
        const data = await getTaskByFileId(currentProject.value.id, file.id)
        const task = data?.task
        const annotations = task?.annotations || task?.pre_annotations || []
        return {
          ...file,
          previewUrl: getFilePreviewUrl(file) || file.downloadUrl || task?.image_url || '',
          annotationCount: Array.isArray(annotations) ? annotations.length : 0,
        }
      } catch (error) {
        console.warn('加载待审核项失败:', error)
        return {
          ...file,
          previewUrl: getFilePreviewUrl(file) || file.downloadUrl || '',
          annotationCount: 0,
        }
      }
    })
  )

  pendingReviewItems.value = reviewItems
}

const closePendingReviewDialog = () => {
  pendingReviewVisible.value = false
  pendingReviewItems.value = []
}

const openPendingReviewItem = async (file) => {
  closePendingReviewDialog()
  if (!currentProject.value) return
  const doneFolder = currentProject.value.folders.find((folder) => folder.name === '已标注')
  if (!doneFolder) return
  currentFolderId.value = doneFolder.id
  await nextTick()
  const index = doneFolder.files.findIndex((item) => item.id === file.id)
  await openAnnotationPreview(file, index >= 0 ? index : 0)
}

const viewCompletedAnnotation = async (file) => {
  try {
    console.log(`[VIEW] 查看已完成标注 | file_id=${file.id}`)

    // 使用过滤后的列表
    const validDoneTasks = doneTasks.value.filter(t => t && t.file_id)
    const cachedTask = validDoneTasks.find((t) => t.file_id === file.id)
    
    if (cachedTask) {
      console.log(`[VIEW] 从缓存找到已完成任务 | task_id=${cachedTask.task_id}`)
      navigateToAnnotate(cachedTask, validDoneTasks.length > 0 ? validDoneTasks : [cachedTask])
      return
    }

    const data = await getTaskByFileId(currentProject.value.id, file.id)
    if (data?.task) {
      console.log(`[VIEW] 从后端获取已完成任务 | task_id=${data.task.task_id}`)
      // 确保传入的数组也经过过滤
      const taskList = validDoneTasks.length > 0 ? validDoneTasks : [data.task].filter(t => t && t.task_id)
      navigateToAnnotate(data.task, taskList)
    } else {
      window.alert('该文件暂无标注结果')
    }
  } catch (error) {
    console.error('加载已完成标注失败:', error)
    window.alert('加载标注结果失败')
  }
}

const navigateToAnnotate = (task, taskList) => {
  // ⚠️ 参数校验 - 确保 task 有效
  if (!task?.task_id) {
    console.error('[NAVIGATE] 错误：task 或 task_id 为空', task)
    window.alert('跳转失败：任务信息不完整')
    return
  }
  
  if (!currentProject.value?.id) {
    console.error('[NAVIGATE] 错误：currentProject 为空')
    window.alert('跳转失败：项目信息丢失，请返回项目列表重试')
    return
  }

  // ⚠️ 关键修复：过滤 taskList 中的 null 元素
  const validTaskList = (taskList || []).filter(t => t && t.task_id)
  
  if (validTaskList.length === 0) {
    console.error('[NAVIGATE] 错误：没有有效的任务列表')
    window.alert('跳转失败：任务列表为空')
    return
  }

  console.log(`[NAVIGATE] 开始跳转 | task_id=${task.task_id}, 有效任务数=${validTaskList.length}`)

  try {
    // 使用过滤后的列表计算索引
    const currentIndex = validTaskList.findIndex((t) => t.task_id === task.task_id)
    
    if (currentIndex === -1) {
      console.error('[NAVIGATE] 错误：在当前任务列表中找不到指定任务', task.task_id)
      window.alert('跳转失败：任务不在当前列表中，请刷新页面重试')
      return
    }

    // 保存任务列表（使用过滤后的）
    localStorage.setItem(
      `task_list_${currentProject.value.id}`,
      JSON.stringify({
        tasks: validTaskList,
        currentIndex: currentIndex,
        projectId: currentProject.value.id,
        projectName: currentProject.value.projectName,
        folderType: currentFolder.value?.name,
      })
    )

    // 保存标注数据
    if (task.annotations && task.annotations.length > 0) {
      localStorage.setItem(
        `pre_annotations_${task.task_id}`,
        JSON.stringify({
          annotations: task.annotations,
          source: 'existing',
          timestamp: Date.now(),
        })
      )
      console.log(
        `[NAVIGATE] 保存已有标注到缓存 | task_id=${task.task_id}, 标注数=${task.annotations.length}`
      )
    } else if (task.pre_annotations && task.pre_annotations.length > 0) {
      localStorage.setItem(
        `pre_annotations_${task.task_id}`,
        JSON.stringify({
          annotations: task.pre_annotations,
          source: 'pre_existing',
          timestamp: Date.now(),
        })
      )
    }

    // 执行跳转
    const routeData = {
      path: '/app/annotate',
      query: {
        projectId: currentProject.value.id,
        task: task.task_id,
        sourceMode: task.use_keywords ? 'keyword' : 'nonKeyword',
        batchSize: String(validTaskList.length),
        projectName: currentProject.value.projectName,
        taskIndex: String(currentIndex),
        totalTasks: String(validTaskList.length),
        fromFolder: currentFolder.value?.name || 'unknown',
      },
    }
    
    console.log('[NAVIGATE] 路由数据:', routeData)
    
    router.push(routeData).catch(err => {
      console.error('[NAVIGATE] 路由跳转失败:', err)
      window.alert('页面跳转失败，请检查网络连接或刷新页面重试')
    })
    
    console.log('[NAVIGATE] ========== 流程结束 ==========')
  } catch (error) {
    console.error('[NAVIGATE] 跳转过程出错:', error)
    window.alert('跳转失败：' + (error.message || '未知错误'))
  }
}

// ============ 工作弹窗相关 ============

const isWorkSelected = (id) => workForm.selectedTagIds.includes(id)

const toggleWorkTag = (tag) => {
  const index = workForm.selectedTagIds.indexOf(tag.id)
  if (index > -1) workForm.selectedTagIds.splice(index, 1)
  else workForm.selectedTagIds.push(tag.id)
}

const removeWorkTag = (id) => {
  const index = workForm.selectedTagIds.indexOf(id)
  if (index > -1) workForm.selectedTagIds.splice(index, 1)
}



const toggleFileSelection = (fileId) => {
  const index = selectedFileIds.value.indexOf(fileId)
  if (index > -1) selectedFileIds.value.splice(index, 1)
  else selectedFileIds.value.push(fileId)
}

const selectAllFilesInFolder = () => {
  if (!currentFolder.value) return
  selectedFileIds.value = currentFolder.value.files.map((file) => file.id)
}

const startSelectedWork = () => {
  if (!currentProject.value || !currentFolder.value) return
  if (!selectedFileIds.value.length) {
    window.alert('请先选择要标注的文件')
    return
  }

  currentWorkFileId.value = selectedFileIds.value[0]
  workForm.mode = currentProject.value.mode || 'keyword'
  workForm.selectedTagIds = []
  workVisible.value = true
}

const closeWorkDialog = () => {
  workVisible.value = false
  currentWorkFileId.value = null
  workForm.mode = 'keyword'
  workForm.selectedTagIds = []
  workForm.confidenceThreshold = 0.25  // 重置为默认值
}

const confirmWorkDialog = async () => {
  console.log('[VUE-100] ========== 开始创建标注会话 ==========')

  if (!currentProject.value) {
    console.log('[VUE-101] ❌ 当前项目为空')
    return
  }

  try {
    const targetFiles = selectedFiles.value.length
      ? selectedFiles.value
      : currentWorkFile.value
      ? [currentWorkFile.value]
      : []

    if (!targetFiles.length) {
      window.alert('请至少选择一张图片')
      return
    }

    console.log(`[VUE-102] 目标文件 | count=${targetFiles.length}`)

    const keywords =
      workForm.mode === 'keyword' ? workSelectedTags.value.map((tag) => tag.name) : []
    
    const confidenceThreshold = workForm.confidenceThreshold

    console.log('[VUE-103] 🚀 调用createAnnotationSession')
   const data = await createAnnotationSession(currentProject.value.id, {
      file_ids: targetFiles.map((file) => file.id),
      use_keywords: workForm.mode === 'keyword',
      keywords,
      confidence_threshold: confidenceThreshold,
    })
    console.log(`[VUE-104] ✅ API调用成功 | tasks=${data.tasks?.length || 0}`)

    // ⚠️ 关键修复：过滤 null 元素
    const rawTasks = data.tasks || []
    const validTasks = rawTasks.filter(t => t && t.task_id && t.file_id)
    
    if (validTasks.length === 0) {
      console.error('[VUE-104b] ❌ 没有有效的任务返回')
      window.alert('创建任务失败：后端返回的任务数据无效')
      return
    }

    if (validTasks.length > 0) {
      localStorage.setItem(`batch_tasks_${data.project_id}`, JSON.stringify(validTasks))

      validTasks.forEach((task) => {
        if (task.annotations && task.annotations.length > 0) {
          localStorage.setItem(
            `pre_annotations_${task.task_id}`,
            JSON.stringify({
              annotations: task.annotations,
              source: 'ai_prediction',
              timestamp: Date.now(),
            })
          )
        }
      })

      localStorage.setItem(
        `project_keywords_${data.project_id}`,
        JSON.stringify({
          use_keywords: data.use_keywords,
          keywords: data.keywords,
          mode: workForm.mode,
        })
      )
    }

    closeWorkDialog()

    console.log('[VUE-105] 等待2秒后刷新...')
    await new Promise((resolve) => setTimeout(resolve, 2000))

    console.log('[VUE-106] 🔄 调用loadProjects()')
    await loadProjects()
    console.log('[VUE-107] ✅ loadProjects()完成')

    await nextTick()
    console.log('[VUE-108] nextTick完成')

    const refreshedProject = projectList.value.find((p) => p.id === currentProjectId.value)
    console.log(`[VUE-109] 刷新后项目查找 | found=${!!refreshedProject}`)

    if (!refreshedProject) {
      console.log('[VUE-110] ❌ 刷新后项目不存在')
      throw new Error('刷新后项目不存在')
    }

    refreshedProject.folders.forEach((folder) => {
      console.log(`[VUE-112] 文件夹[${folder.name}] | count=${folder.files.length}`)
    })

    const pendingFolder = refreshedProject.folders.find((f) => f.name === '待标注')
    const targetFileIds = new Set(targetFiles.map((f) => f.id))
    const stillInPending = pendingFolder?.files.some((f) => targetFileIds.has(f.id))

    console.log(`[VUE-114] 文件状态检查 | stillInPending=${stillInPending}`)

    if (stillInPending) {
      console.log('[VUE-115] ⚠️ 警告：文件仍在待标注文件夹')
      console.log('[VUE-116] 🔄 执行第二次刷新')
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await loadProjects()
      await nextTick()
    }

    const labelingFolder = refreshedProject.folders?.find((f) => f.name === '标注中')
    if (labelingFolder) {
      currentFolderId.value = labelingFolder.id
      selectedFileIds.value = []
      console.log(`[VUE-117] ✅ 切换到标注中文件夹 | files=${labelingFolder.files.length}`)
    }

    console.log('[VUE-118] 跳转到标注页面')

    const firstTask = validTasks[0]
    const taskList = validTasks.map((t) => ({
      task_id: t.task_id,
      file_id: t.file_id,
      filename: t.filename,
      image_url: t.image_url,
      status: 'labeling',
      project_name: t.project_name,
      project_id: data.project_id,
      use_keywords: t.use_keywords,
      keywords: t.keywords,
      annotations: t.annotations || [],
    }))
    
    // ⚠️ 再次过滤确保没有 null
    const finalTaskList = taskList.filter(t => t && t.task_id)

    navigateToAnnotate(firstTask, finalTaskList)
    console.log('[VUE-119] ========== 流程结束 ==========')
  } catch (error) {
    console.error('[VUE-120] ❌ 创建标注任务失败:', error)
    window.alert(error?.response?.data?.detail || error.message || '创建标注任务失败')
  }
}
// ============ 项目操作 ============

const openRenameDialog = (project) => {
  closeProjectMenu()
  renameProjectId.value = project.id
  renameValue.value = project.projectName
  renameVisible.value = true
}

const closeRenameDialog = () => {
  renameVisible.value = false
  renameProjectId.value = null
  renameValue.value = ''
}

const confirmRename = () => {
  if (renameError.value) return

  const target = projectList.value.find((item) => item.id === renameProjectId.value)
  if (!target) return

  target.projectName = renameValue.value.trim()
  closeRenameDialog()
}

const deleteProject = async (projectId) => {
  closeProjectMenu()

  if (deletingProjectId.value === projectId) return

  const target = projectList.value.find((item) => item.id === projectId)
  if (!target) return

  const confirmed = window.confirm(`确定删除项目"${target.projectName}"吗？`)
  if (!confirmed) return

  try {
    deletingProjectId.value = projectId

    await deleteProjectApi(projectId)

    if (currentProjectId.value === projectId) {
      backToProjectList()
    }

    await loadProjects()
  } catch (error) {
    console.error('删除项目失败：', error)
    window.alert(error?.response?.data?.detail || error.message || '删除项目失败')
  } finally {
    deletingProjectId.value = null
  }
}

const closeProgressSocket = () => {
  progressSocketStopped.value = true
  if (progressSocket.value) {
    progressSocket.value.close()
    progressSocket.value = null
  }
}

const connectProgressSocket = () => {
  progressSocketStopped.value = false
  closeProgressSocket()
  progressSocketStopped.value = false
  
  // 强制从 localStorage 读取最新 token，并检查有效性
  const rawToken = localStorage.getItem('token')
  if (!rawToken) {
    console.log('[WebSocket] 无可用 token，跳过连接')
    return
  }

  // 简单检查 token 格式（不解析，避免性能开销）
  try {
    const payload = JSON.parse(atob(rawToken.split('.')[1]))
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      console.warn('[WebSocket] Token 已过期，尝试重新登录')
      // 可选：自动跳转到登录页
      // router.push('/login')
      return
    }
  } catch {
    console.error('[WebSocket] Token 格式无效')
    return
  }

  const token = rawToken
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${wsProtocol}://${window.location.host}/api/ws/progress?token=${encodeURIComponent(token)}`
  
  console.log('[WebSocket] 连接中...', wsUrl.replace(/token=.*/, 'token=***'))
  
  const socket = new WebSocket(wsUrl)
  progressSocket.value = socket

  socket.onopen = () => {
    console.log('[WebSocket] 连接成功')
  }

  socket.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data || '{}')
      if (message.type !== 'PROJECT_PROGRESS_UPDATED') return

      const activeProjectId = currentProject.value?.id
      await loadProjects()
      if (activeProjectId) {
        currentProjectId.value = activeProjectId
        if (isLabelingFolder.value || isDoneFolder.value) {
          await loadFolderTasks()
        }
      }
    } catch (error) {
      console.warn('[WebSocket] 解析消息失败:', error)
    }
  }

  socket.onerror = (error) => {
    console.error('[WebSocket] 连接错误:', error)
  }

  socket.onclose = (event) => {
    console.log('[WebSocket] 连接关闭:', event.code, event.reason)
    
    if (progressSocketStopped.value) return
    
    // 403 错误不重连（token 问题）
    if (event.code === 1008) {
      console.warn('[WebSocket] 认证失败，停止重连')
      return
    }
    
    if (progressSocket.value === socket) {
      progressSocket.value = null
      window.setTimeout(() => connectProgressSocket(), 3000)  // 延长重连间隔
    }
  }
}

// ============ 菜单操作 ============

const handleGlobalClick = () => closeProjectMenu()

const toggleProjectMenu = (projectId) => {
  openedProjectMenuId.value = openedProjectMenuId.value === projectId ? null : projectId
}

const closeProjectMenu = () => {
  openedProjectMenuId.value = null
}

const handleRenameFromMenu = (project) => {
  closeProjectMenu()
  openRenameDialog(project)
}

const handleDeleteFromMenu = (projectId) => {
  closeProjectMenu()
  deleteProject(projectId)
}

// ============ 生命周期 ============

watch(
  () => workForm.mode,
  (newMode) => {
    if (newMode === 'nonKeyword') workForm.selectedTagIds = []
  }
)

watch(
  () => userStore.token,
  (token) => {
    if (!token) {
      closeProgressSocket()
      return
    }
    connectProgressSocket()
  }
)

onMounted(() => {
  loadProjects()
  connectProgressSocket()
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('resize', handleResize)

  window.addEventListener('message', (event) => {
    if (event.data === 'refresh-project') {
      loadProjects()
      if (isLabelingFolder.value) {
        loadFolderTasks()
      }
    }
  })
})

onBeforeUnmount(() => {
  if (previewImageUrl.value && previewImageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImageUrl.value)
  }

  previewUrlMap.forEach((url) => URL.revokeObjectURL(url))
  previewUrlMap.clear()
 // 清理 URL 缓存
  urlCache.clear()
  imageLoadCache.clear()
  preloadQueue.clear()
  
  // 清理 blob URL
  previewUrlMap.forEach((url) => {
    if (url.startsWith('blob:')) {
      URL.revokeObjectURL(url)
    }
  })
  previewUrlMap.clear()

  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('resize', handleResize)
  closeProgressSocket()
})
</script>

<style scoped>
.project-content-page {
  width: 100%;
  padding: 24px;
  box-sizing: border-box;
}

.project-toolbar {
  margin-bottom: 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-input,
.toolbar-select {
  height: 42px;
  border: 1px solid #d8dee6;
  border-radius: 12px;
  background: #fff;
  font-size: 14px;
  color: #111827;
  box-sizing: border-box;
  outline: none;
}

.toolbar-input {
  width: 240px;
  padding: 0 14px;
}

.team-toolbar-input {
  width: 300px;
}

.toolbar-select {
  padding: 0 14px;
}

.toolbar-input:focus,
.toolbar-select:focus {
  border-color: #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.12);
}

.project-count {
  font-size: 14px;
  color: #6b7280;
}

.project-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: flex-start;
}

.project-folder-card--shared {
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.project-folder-card--shared-pending {
  opacity: 0.72;
}

.project-folder-card--shared-pending .folder-click-area {
  filter: grayscale(0.18);
}

.shared-project-badge {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #4f46e5;
}

.project-team-badge,
.project-pending-acceptance {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.project-pending-acceptance {
  color: #92400e;
}
.project-folder-card {
  position: relative;
  width: 260px;
  user-select: none;
}

.folder-click-area {
  cursor: pointer;
}

.folder-preview {
  position: relative;
  width: 100%;
  height: 185px;
  border-radius: 18px;
  background: #f7f7f7;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.project-review-dot {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.95);
  z-index: 3;
}

.project-folder-card:hover .folder-preview {
  background: #f3f4f6;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
}

.small-folder-preview {
  height: 160px;
  cursor: pointer;
}

.folder-shape {
  position: relative;
  width: 92px;
  height: 60px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f6cf70, #efbc46);
  box-shadow: inset 0 -4px 0 rgba(0, 0, 0, 0.05);
  z-index: 1;
}

.folder-tab {
  position: absolute;
  top: -10px;
  left: 12px;
  width: 34px;
  height: 16px;
  border-radius: 10px 10px 0 0;
  background: #e9b94d;
}

.folder-name {
  margin-top: 16px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  color: #111827;
  word-break: break-word;
}

.folder-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
}

.project-card-menu-wrap {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
}

.project-menu-trigger {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: #4b5563;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.project-menu-trigger:hover {
  background: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.project-menu-dropdown {
  position: absolute;
  top: 42px;
  right: 0;
  min-width: 120px;
  padding: 8px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
  border: 1px solid rgba(229, 231, 235, 0.9);
}

.project-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  color: #1f2937;
  cursor: pointer;
}

.project-menu-item:hover {
  background: #f3f4f6;
}

.project-menu-item.danger {
  color: #dc2626;
}

.project-menu-item.danger:hover {
  background: #fef2f2;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.folder-count {
  margin-top: 8px;
  font-size: 14px;
  color: #6b7280;
}

.folder-remark-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  background: rgba(17, 24, 39, 0.58);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  box-sizing: border-box;
}

.folder-remark-text {
  max-width: 100%;
  max-height: 100%;
  overflow-y: auto;
  color: #ffffff;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
  word-break: break-word;
  white-space: pre-wrap;
}

.project-detail-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 28px;
}

.project-nav {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 44px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #e5e7eb;
  border-radius: 50%;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease,
    border-color 0.18s ease;
}

.back-btn:hover {
  background: #f8fafc;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.back-btn:active {
  transform: translateY(0);
}

.back-btn-icon {
  font-size: 18px;
  line-height: 1;
  transform: translateX(-1px);
}

.breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.breadcrumb-link {
  color: #6b7280;
  cursor: pointer;
  transition: color 0.18s ease;
}

.breadcrumb-link:hover {
  color: #111827;
}

.breadcrumb-separator {
  color: #c0c4cc;
}

.breadcrumb-current {
  color: #111827;
  font-weight: 600;
  word-break: break-word;
}

.project-detail-title-wrap {
  min-width: 0;
}

.project-detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.project-detail-title {
  font-size: 28px;
  font-weight: 800;
  color: #111827;
  line-height: 1.3;
}

.pending-review-btn {
  margin-left: auto;
  border: 1px solid #fca5a5;
  background: #fff1f2;
  color: #be123c;
  border-radius: 999px;
  height: 34px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.pending-review-badge {
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 12px;
  line-height: 20px;
  padding: 0 6px;
  text-align: center;
}

.project-detail-remark {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: #6b7280;
  white-space: pre-wrap;
  word-break: break-word;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 18px;
}

.image-card {
  position: relative;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.folder-action-buttons {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.file-select-checkbox {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.file-select-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.image-card-preview {
  width: 100%;
  aspect-ratio: 1 / 1;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}

.image-thumb {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #f8fafc;
}

.image-placeholder,
.file-placeholder {
  font-size: 14px;
  color: #9aa1a9;
}

.file-placeholder {
  font-size: 40px;
}

.image-card-info {
  padding: 12px 12px 8px;
  min-height: 60px;
}

.file-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

/* 文件状态标签 */
.file-status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.file-status-tag.pending {
  background: #fef3c7;
  color: #92400e;
}

.file-status-tag.labeling {
  background: #dbeafe;
  color: #1e40af;
}

.file-status-tag.done {
  background: #d1fae5;
  color: #065f46;
}

.image-card-actions {
  padding: 0 12px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-folder-page,
.empty-project-state {
  font-size: 14px;
  color: #9aa1a9;
  padding: 12px 2px;
}

.empty-project-state {
  margin-top: 24px;
}

.dialog-btn,
.file-action-btn {
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.18s ease, filter 0.18s ease, box-shadow 0.18s ease;
}

.dialog-btn:hover,
.file-action-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
}

.file-action-btn {
  padding: 6px 12px;
  font-size: 12px;
  line-height: 1;
}

.file-action-btn.preview {
  background: #e0f2fe;
  color: #0369a1;
}

.file-action-btn.work {
  background: #dcfce7;
  color: #166534;
}

/* 继续标注按钮 */
.file-action-btn.continue-btn {
  background: linear-gradient(135deg, #43c7db, #2faec6);
  color: white;
}

.file-action-btn.continue-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  filter: none;
}

/* 查看按钮 */
.file-action-btn.review-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
}

.file-action-btn.review-btn:hover {
  filter: brightness(1.1);
}

.dialog-mask,
.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.dialog-panel {
  width: min(420px, 92vw);
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  padding: 22px;
  box-sizing: border-box;
}

.dialog-panel.work-dialog-panel {
  width: min(840px, 96vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.work-dialog-header {
  padding: 22px 22px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.work-dialog-close {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: transparent;
  font-size: 26px;
  line-height: 1;
  color: #999;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
  flex-shrink: 0;
}

.work-dialog-close:hover {
  background: #f3f4f6;
  color: #666;
}

.dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-body {
  margin-top: 16px;
}

.work-dialog-body {
  padding: 18px 22px 0;
  overflow-y: auto;
}

.work-file-summary {
  margin-bottom: 16px;
  font-size: 14px;
  color: #6b7280;
  word-break: break-all;
}

.work-file-summary span {
  color: #111827;
  font-weight: 600;
}

.mode-row {
  display: flex;
  align-items: center;
  gap: 48px;
  margin: 8px 0 18px;
  flex-wrap: wrap;
}

.radio-item {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.radio-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #a6a6a6;
  margin-right: 10px;
  box-sizing: border-box;
  position: relative;
  flex-shrink: 0;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.radio-dot.active {
  border-color: #3c8596;
}

.radio-dot.active::after {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 50%;
  background: #3c8596;
}

.radio-item:hover .radio-dot {
  transform: scale(1.05);
}

.radio-text {
  font-size: 15px;
  color: #737373;
}

.radio-text.strong {
  font-weight: 700;
  color: #1f2937;
}

.tag-panel {
  background: #fafafa;
  border-radius: 10px;
  padding: 16px;
}

.selected-title {
  font-size: 15px;
  color: #2b2f36;
  margin-bottom: 10px;
  font-weight: 600;
}

.selected-box {
  min-height: 76px;
  border: 2px solid #b8b8b8;
  border-radius: 14px;
  background: #fff;
  padding: 14px;
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}

.scene-block {
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid #dddddd;
}

.scene-title {
  font-size: 15px;
  font-weight: 700;
  color: #2b2f36;
  margin-bottom: 14px;
}

.scene-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tag-chip {
  position: relative;
  border: none;
  border-radius: 14px;
  padding: 10px 14px;
  font-size: 14px;
  color: #2d3748;
  cursor: pointer;
  line-height: 1;
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.tag-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
  filter: brightness(1.02);
}

.tag-chip.selected {
  padding-right: 32px;
}

.scene-chip.active {
  box-shadow: 0 0 0 2px rgba(88, 121, 91, 0.16);
}

.tag-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #95a47b;
  background: #dce8cb;
  color: #7d8e68;
  font-size: 18px;
  line-height: 16px;
  cursor: pointer;
  padding: 0;
}

.tag-remove.small {
  position: absolute;
  top: -8px;
  right: -8px;
}

.empty-text {
  font-size: 13px;
  color: #9aa1a9;
}

.dialog-input {
  width: 100%;
  height: 44px;
  border: 1px solid #d8dee6;
  border-radius: 12px;
  padding: 0 14px;
  box-sizing: border-box;
  outline: none;
  font-size: 14px;
}

.dialog-input:focus {
  border-color: #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.12);
}

.dialog-error {
  margin-top: 8px;
  font-size: 13px;
  color: #d14343;
}

.dialog-footer {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.work-dialog-panel .dialog-footer {
  margin-top: 0;
  padding: 20px 32px 28px;
  justify-content: flex-end;
}

.dialog-btn {
  padding: 9px 16px;
  font-size: 14px;
}

.dialog-btn.secondary {
  background: #eef2f7;
  color: #374151;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #43c7db, #2faec6);
  color: #fff;
}

.preview-panel {
  position: relative;
  width: min(980px, 92vw);
  max-height: 90vh;
  background: #ffffff;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  display: flex;
  flex-direction: column;
}

.preview-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(17, 24, 39, 0.72);
  color: #fff;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.preview-content {
  flex: 1;
  min-height: 0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 24px;
  box-sizing: border-box;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 12px;
}

.preview-footer {
  padding: 14px 18px 18px;
  border-top: 1px solid #eef2f7;
}

.preview-file-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}

.mask-fade-enter-active,
.mask-fade-leave-active,
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.2s ease;
}

.mask-fade-enter-from,
.mask-fade-leave-to,
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .project-content-page {
    padding: 16px;
  }

  .project-toolbar {
    margin-bottom: 18px;
  }

  .toolbar-input {
    width: 100%;
  }

  .project-detail-title {
    font-size: 24px;
  }

  .image-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .folder-action-buttons {
    width: 100%;
    margin-top: 12px;
  }
}

/* ========== 大图标注预览弹窗 - 修复标注框偏差 ========== */

/* 遮罩层 */
.annotation-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

/* 弹窗容器 - 和页面等高 */
.annotation-preview-panel {
  position: relative;
  width: 90vw;
  height: 100vh;
  max-width: 1400px;
  background: #ffffff;
  border-radius: 0;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

/* 顶部工具栏 */
.preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  height: 64px;
  box-sizing: border-box;
  flex-shrink: 0;
}

.toolbar-info {
  display: flex;
  align-items: center;
  gap: 16px;
  color: #374151;
}

.file-counter {
  font-size: 14px;
  font-weight: 600;
  background: #f3f4f6;
  padding: 6px 14px;
  border-radius: 20px;
  color: #111827;
}

.file-name {
  font-size: 15px;
  font-weight: 500;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #6b7280;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

.toolbar-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-continue {
  background: linear-gradient(135deg, #43c7db, #2faec6);
  color: white;
}

.btn-continue:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
}

.btn-close {
  background: #f3f4f6;
  color: #6b7280;
  width: 36px;
  height: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.btn-close:hover {
  background: #e5e7eb;
  color: #374151;
}

/* 图片内容区 - 关键：使用 flex 布局让容器自动计算尺寸 */
.annotation-preview-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
  position: relative;
  background: #f9fafb;
}

/* 图片包装器 - 填满可用空间 */
.annotation-image-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 关键：图片容器 - 通过 JS 计算精确尺寸 */
.annotation-image-container {
  position: relative;
  /* 尺寸由 JS 计算的 style 绑定控制 */
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* 图片 - 填满容器 */
.annotation-preview-image {
  width: 100%;
  height: 100%;
  object-fit: fill; /* 关键：填满容器，不保持比例，由容器控制比例 */
  display: block;
}

/* 关键：SVG 标注层 - 与容器完全重叠，使用 viewBox 保持比例 */
.annotation-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}

/* 底部信息栏 */
.annotation-preview-footer {
  padding: 16px 24px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  min-height: 56px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-shrink: 0;
}

.annotation-stats {
  display: flex;
  gap: 24px;
  color: #6b7280;
  font-size: 14px;
}

.stat-item {
  background: #f3f4f6;
  padding: 8px 16px;
  border-radius: 20px;
  color: #374151;
}

.stat-item.source {
  background: #dbeafe;
  color: #1e40af;
}

.stat-item.empty {
  color: #9ca3af;
  background: #f9fafb;
}

.annotation-label-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.annotation-label-chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 12px;
  line-height: 1.2;
}

/* 左右切换箭头 */
.nav-arrow {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 96px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #374151;
  font-size: 32px;
  cursor: pointer;
  z-index: 10001;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.nav-arrow:hover {
  background: #ffffff;
  transform: translateY(-50%) scale(1.05);
}

.nav-prev {
  left: calc(5vw - 24px);
}

.nav-next {
  right: calc(5vw - 24px);
}

/* 响应式 */
@media (max-width: 768px) {
  .annotation-preview-panel {
    width: 100vw;
  }

  .nav-prev {
    left: 8px;
  }

  .nav-next {
    right: 8px;
  }

  .file-name {
    max-width: 200px;
  }

  .preview-toolbar {
    padding: 12px 16px;
    height: 56px;
  }

  .annotation-preview-content {
    padding: 16px;
  }

  .nav-arrow {
    width: 40px;
    height: 72px;
    font-size: 24px;
  }
}
</style>
<style scoped>
.page-top-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .page-top-actions {
    margin-bottom: 16px;
  }
}
/* 添加样式优化 */
.annotation-overlay text {
  user-select: none;
  pointer-events: none;
}
.annotation-labels-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* 修改 .annotation-label 移除固定红色背景 */
.annotation-label {
  position: absolute;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  font-family: system-ui, -apple-system, sans-serif;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  transform: translateY(-100%); /* 默认向上 */
  margin-top: -4px;
  z-index: 10;
  pointer-events: none;
}

.label-text {
  display: inline-block;
  line-height: 1.2;
}

.annotation-label.label-below {
  transform: translateY(0);
  margin-top: 4px;
}

/* 图片加载优化样式 */
.image-thumb {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading-shimmer 1.5s infinite;
}

.image-thumb[src] {
  animation: none;
  background: #f8fafc;
}

@keyframes loading-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 减少重绘优化 */
.image-card {
  contain: layout style paint;
  content-visibility: auto;
}

/* 置信度阈值设置样式 */
.confidence-section {
  margin-top: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 12px;
  border: 1px solid #bae6fd;
}

.confidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.confidence-title {
  font-size: 15px;
  font-weight: 600;
  color: #0369a1;
}

.confidence-value {
  font-size: 18px;
  font-weight: 700;
  color: #0284c7;
  background: #ffffff;
  padding: 4px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.15);
}

.confidence-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}

.slider-container {
  padding: 0 8px;
}

.slider-container :deep(.el-slider__runway) {
  height: 8px;
  border-radius: 4px;
  background-color: #e0f2fe;
}

.slider-container :deep(.el-slider__bar) {
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(90deg, #38bdf8 0%, #0284c7 100%);
}

.slider-container :deep(.el-slider__button) {
  width: 20px;
  height: 20px;
  border: 3px solid #0284c7;
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.3);
}

.slider-container :deep(.el-slider__marks-text) {
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
}

.confidence-hint {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 12px;
}

.hint-low {
  color: #059669;
  font-weight: 500;
}

.hint-high {
  color: #dc2626;
  font-weight: 500;
}


/* 数据导出按钮样式 */
.file-action-btn.export-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
}

.file-action-btn.export-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.file-action-btn.export-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  filter: none;
}

/* 导出弹窗样式 */
.export-dialog-panel {
  width: min(600px, 96vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.export-dialog-header {
  padding: 24px 24px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.export-dialog-close {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  font-size: 28px;
  line-height: 1;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
}

.export-dialog-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.export-dialog-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.export-summary {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #f0f9ff;
  border-radius: 10px;
  border-left: 4px solid #0ea5e9;
}

.export-count {
  font-size: 15px;
  font-weight: 600;
  color: #0369a1;
}

.export-hint {
  font-size: 13px;
  color: #64748b;
  margin-left: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 格式选项样式 */
.export-format-section {
  margin-bottom: 24px;
}

.format-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.format-option {
  display: flex;
  align-items: center;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
}

.format-option:hover {
  border-color: #c7d2fe;
  background: #f8fafc;
}

.format-option.active {
  border-color: #667eea;
  background: #eef2ff;
}

.format-icon {
  font-size: 28px;
  margin-right: 16px;
  flex-shrink: 0;
}

.format-info {
  flex: 1;
}

.format-name {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 4px;
}

.format-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.4;
}

.format-check {
  margin-left: 12px;
}

.check-circle {
  width: 24px;
  height: 24px;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.check-circle.checked {
  background: #667eea;
  border-color: #667eea;
}

.check-circle.checked::after {
  content: '✓';
  color: white;
  font-size: 14px;
  font-weight: bold;
}

/* 导出选项样式 */
.export-options-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 12px;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.option-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin-right: 10px;
  accent-color: #667eea;
  cursor: pointer;
}

.option-text {
  user-select: none;
}

.split-ratio-inputs {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  margin-left: 28px;
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.ratio-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ratio-item label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.ratio-item input {
  width: 60px;
  height: 32px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
}

.ratio-item span {
  font-size: 13px;
  color: #6b7280;
}

/* 类别映射样式 */
.class-mapping-section {
  margin-bottom: 20px;
}

.class-mapping-hint {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 12px;
}

.detected-classes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.class-item {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #f3f4f6;
  border-radius: 20px;
  font-size: 13px;
}

.class-id {
  width: 20px;
  height: 20px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  margin-right: 8px;
}

.class-name {
  color: #374151;
  font-weight: 500;
}

.export-footer {
  margin-top: 0;
  padding: 20px 24px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-btn.export-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  padding: 10px 24px;
}

.dialog-btn.export-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
</style>