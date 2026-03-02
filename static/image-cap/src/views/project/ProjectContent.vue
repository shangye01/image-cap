<template>
  <div class="publish-container">

    <!-- 左侧：上传区域 -->
    <div class="upload-section">
      <div class="ant-upload ant-upload-drag">
        <span class="ant-upload-btn" role="button">
          <input 
            type="file" 
            accept="image/*,.heic,.psd,.heif" 
            multiple 
            style="display:none;"
          />
          
          <div class="ant-upload-drag-container">
            <div class="upload-content">
              
              <div class="upload-icon">
                <img src="https://grocery-cdn.huaban.com/file/hb_add_icon.svg" width="33" height="33" />
                <!-- <img src="https://grocery-cdn.huaban.com/file/hb_upload_icon.svg" width="40" height="40" /> -->
              </div>

              <div class="upload-text">
                拖放文件或点击添加
              </div>

              <div class="upload-tip">
                每次最多上传 50 个文件，单个图片不超过 20 MB
              </div>

            </div>
          </div>
        </span>
      </div>
    </div>


    <!-- 右侧：表单区域 -->
    <div class="form-section">

      <!-- 选择画板 -->
      <div class="form-item">
        <div class="ant-select ant-select-single">
          <div class="ant-select-selector">
            <input type="search" />
            <span class="ant-select-selection-placeholder">
              * 项目名称
            </span>
          </div>
        </div>
      </div>

      <!-- 描述 -->
      <div class="form-item">
        <textarea 
          class="ant-input"
          placeholder="添加描述"
        ></textarea>
      </div>

      <!-- 选择活动 -->
      <div class="form-item">
        <div class="ant-select ant-select-single">
          <div class="ant-select-selector">
            <span class="ant-select-selection-placeholder">
              选择类别
            </span>
          </div>
        </div>
      </div>

      <!-- 标签 -->
      <div class="form-item">
        <div class="ant-select ant-select-multiple">
          <div class="ant-select-selector">
            <span class="ant-select-selection-placeholder">
              标签
            </span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
<style scoped>

/* =======================
   页面整体布局
======================= */

.publish-container {
  display: flex;
  justify-content: center;
  gap: 64px;

  padding: 24px 0;
}


/* =======================
   左侧上传区域
======================= */

.upload-section {
  width: 520px;
}

.ant-upload-drag {
  width: 100%;
  height: 540px;

  background: #f3f4f6;
  border-radius: 28px;
  border: 6px solid #e5e7eb;

  display: flex;
  align-items: center;
  justify-content: center;

  transition: all 0.25s ease;
  cursor: pointer;
}

.ant-upload-drag:hover {
  border-color: #d1d5db;
  background: #f0f2f5;
}

.ant-upload-btn {
  width: 100%;
  height: 100%;
}

.ant-upload-drag-container {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-content {
  text-align: center;
}

.upload-icon {
  margin-bottom: 20px;
}

.upload-icon img:first-child {
  display: block;
  margin: 0 auto 8px;
}

.upload-text {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20px;
}

.upload-tip {
  font-size: 14px;
  color: #9ca3af;
}


/* =======================
   右侧表单区域
======================= */

.form-section {
  width: 480px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}


/* 通用输入块 */
.form-item {
  width: 100%;
}


/* =======================
   Select 样式模拟 Ant 风格
======================= */

.ant-select-selector,
.ant-input,
textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: #ffffff;

  padding: 16px 18px;
  font-size: 15px;
  color: #111827;

  transition: all 0.2s ease;
}

.ant-select-selector:hover,
.ant-input:hover,
textarea:hover {
  border-color: #d1d5db;
}

.ant-select-selector:focus-within,
.ant-input:focus,
textarea:focus {
  outline: none;
  border-color: #111827;
}


/* =======================
   Textarea 特殊高度
======================= */

textarea {
  min-height: 140px;
  resize: none;
}


/* Placeholder 颜色 */
.ant-select-selection-placeholder {
  color: #9ca3af;
}


/* 来源链接输入 */
input.ant-input {
  height: 52px;
}


/* =======================
   响应式
======================= */

@media (max-width: 1200px) {
  .publish-container {
    flex-direction: column;
    align-items: center;
  }

  .upload-section,
  .form-section {
    width: 90%;
  }
}

</style>