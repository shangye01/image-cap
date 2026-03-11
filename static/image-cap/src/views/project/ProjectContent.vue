<template>
  <div class="create-board-card" data-gd-click="button_click" data-button-name="create">
    <div class="upload-box" @click="openDialog">
      <div class="plus">+</div>
    </div>

    <div class="title">创建</div>
    <div class="desc">创建你的项目</div>
  </div>

  <teleport to="body">
    <transition name="fade-mask">
      <div v-if="visible" class="modal-mask" @click="closeDialog">
        <transition name="zoom-dialog" appear>
          <div class="modal-panel" @click.stop>
            <div class="modal-header">
              <div class="modal-title">创建</div>
              <button class="close-btn" @click="closeDialog">×</button>
            </div>

            <div class="modal-body">
              <div class="form-item">
                <label class="form-label">项目名<span class="required">*</span></label>
                <input v-model="form.projectName" class="text-input" />
              </div>

              <div class="form-item">
                <label class="form-label">备注<span class="required">*</span></label>
                <textarea v-model="form.remark" class="textarea-input"></textarea>
              </div>

              <div class="mode-row">
                <label class="radio-item" @click="form.mode = 'keyword'">
                  <span class="radio-dot" :class="{ active: form.mode === 'keyword' }"></span>
                  <span class="radio-text strong">关键词模型</span>
                </label>

                <label class="radio-item" @click="form.mode = 'nonKeyword'">
                  <span class="radio-dot" :class="{ active: form.mode === 'nonKeyword' }"></span>
                  <span class="radio-text">非关键词模型</span>
                </label>
              </div>

              <div class="tag-panel">
                <div class="selected-title">已选择的标签</div>

                <div class="selected-box">
                  <template v-if="selectedTags.length">
                    <div
                      v-for="tag in selectedTags"
                      :key="tag.id"
                      class="tag-chip selected"
                      :style="{ backgroundColor: tag.color }"
                    >
                      <span>{{ tag.name }}</span>
                      <button class="tag-remove" @click="removeTag(tag.id)">×</button>
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
                      class="tag-chip scene-chip"
                      :class="{ active: isSelected(tag.id) }"
                      :style="{ backgroundColor: tag.color }"
                      @click="toggleTag(tag)"
                    >
                      <span>{{ tag.name }}</span>
                      <span v-if="isSelected(tag.id)" class="tag-remove small">×</span>
                    </button>
                  </div>
                </div>
              </div>
              <div class="modal-footer">
                <button class="create-btn" @click="submitCreate">创建</button>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const emit = defineEmits(['create'])

const visible = ref(false)

const form = reactive({
  projectName: '',
  remark: '',
  mode: 'keyword',
  selectedTagIds: [], // 不默认选择
})

const scenes = ref([
  {
    id: 1,
    name: '场景1',
    tags: [
      { id: 1, name: '标签1', color: '#d9c2f2' },
      { id: 2, name: '标签2', color: '#f4b4af' },
      { id: 3, name: '标签3', color: '#b8c9f6' },
      { id: 4, name: '标签4', color: '#ecd68d' },
      { id: 5, name: '标签5', color: '#a9cf96' },
    ],
  },
  {
    id: 2,
    name: '场景2',
    tags: [
      { id: 6, name: '标签1', color: '#aee9ec' },
      { id: 7, name: '标签2', color: '#f2d562' },
      { id: 8, name: '标签3', color: '#eea2ca' },
    ],
  },
])

const allTags = computed(() => scenes.value.flatMap((scene) => scene.tags))

const selectedTags = computed(() =>
  allTags.value.filter((tag) => form.selectedTagIds.includes(tag.id))
)

const openDialog = () => {
  visible.value = true
}

const closeDialog = () => {
  visible.value = false
}

const isSelected = (id) => {
  return form.selectedTagIds.includes(id)
}

const toggleTag = (tag) => {
  const index = form.selectedTagIds.indexOf(tag.id)
  if (index > -1) {
    form.selectedTagIds.splice(index, 1)
  } else {
    form.selectedTagIds.push(tag.id)
  }
}

const removeTag = (id) => {
  const index = form.selectedTagIds.indexOf(id)
  if (index > -1) {
    form.selectedTagIds.splice(index, 1)
  }
}

const resetForm = () => {
  form.projectName = ''
  form.remark = ''
  form.mode = 'keyword'
  form.selectedTagIds = []
}

const submitCreate = () => {
  if (!form.projectName.trim()) {
    alert('请输入项目名')
    return
  }

  if (!form.remark.trim()) {
    alert('请输入备注')
    return
  }

  emit('create', {
    projectName: form.projectName.trim(),
    remark: form.remark.trim(),
    mode: form.mode,
    selectedTags: selectedTags.value,
  })

  closeDialog()
  resetForm()
}
</script>

<style scoped>
.create-board-card {
  width: 260px;
  cursor: pointer;
  user-select: none;
}

.upload-box {
  width: 100%;
  height: 185px;
  border: 2px dashed #d9d9d9;
  border-radius: 18px;
  background: #f7f7f7;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background-color 0.2s ease, transform 0.2s ease,
    box-shadow 0.2s ease;
  box-sizing: border-box;
}

.plus {
  font-size: 56px;
  line-height: 1;
  color: #222;
  font-weight: 400;
  transform: translateY(-2px);
}

.title {
  margin-top: 16px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  color: #111827;
}

.desc {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.6;
  color: #6b7280;
}

.create-board-card:hover .upload-box {
  border-color: #c7c7c7;
  background: #f3f4f6;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
}

.create-board-card:active .upload-box {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(240, 240, 240, 0.72);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.modal-panel {
  width: min(640px, 92vw);
  max-height: 88vh;

  display: flex;
  flex-direction: column;

  background: #fff;
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.12);

  overflow: hidden;
}

.modal-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #ececec;
  flex-shrink: 0;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #5f6670;
  margin: 0;
}

.modal-body {
  flex: 1;
  overflow-y: auto;

  padding: 18px 24px 24px;
}

.modal-footer {
  margin-top: 28px;
  display: flex;
  justify-content: flex-end;
}

.form-item {
  margin-bottom: 18px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #2b2f36;
}

.required {
  color: #c85c5c;
  margin-left: 2px;
}

.text-input,
.textarea-input {
  width: 100%;
  border: 2px solid #b8b8b8;
  border-radius: 14px;
  outline: none;
  font-size: 14px;
  color: #333;
  box-sizing: border-box;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.text-input {
  height: 46px;
  padding: 0 14px;
}

.textarea-input {
  min-height: 120px;
  padding: 12px 14px;
  resize: vertical;
}

.text-input:hover,
.textarea-input:hover {
  border-color: #9aa8b0;
}

.text-input:focus,
.textarea-input:focus {
  border-color: #45b8cb;
  box-shadow: 0 0 0 4px rgba(69, 184, 203, 0.12);
  background: #fcfeff;
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

.empty-text {
  font-size: 13px;
  color: #9aa1a9;
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

.create-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 26px;
  font-size: 16px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, #43c7db, #2faec6);
  box-shadow: 0 10px 20px rgba(47, 174, 198, 0.25);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.create-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(47, 174, 198, 0.3);
  filter: brightness(1.02);
}

.create-btn:active {
  transform: translateY(0);
}

.close-btn {
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

.close-btn:hover {
  background: #f3f4f6;
  color: #666;
}

.fade-mask-enter-active,
.fade-mask-leave-active {
  transition: opacity 0.22s ease;
}

.fade-mask-enter-from,
.fade-mask-leave-to {
  opacity: 0;
}

.zoom-dialog-enter-active,
.zoom-dialog-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.zoom-dialog-enter-from,
.zoom-dialog-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
}

@media (max-width: 640px) {
  .modal-mask {
    padding: 14px;
  }

  .modal-panel {
    width: 100%;
    max-height: 90vh;
    border-radius: 18px;
  }

  .modal-header {
    padding: 16px 16px 12px;
  }

  .modal-body {
    padding: 14px 16px;
  }

  .modal-footer {
    padding: 12px 16px 16px;
  }

  .modal-title {
    font-size: 20px;
  }

  .form-label,
  .selected-title,
  .scene-title {
    font-size: 14px;
  }

  .mode-row {
    gap: 18px;
  }

  .radio-text {
    font-size: 14px;
  }

  .create-btn {
    font-size: 15px;
    padding: 10px 22px;
  }
}
</style>