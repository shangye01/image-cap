<template>
  <Transition name="fade">
    <div 
      v-if="visible" 
      class="dialog-overlay"
      @click.self="handleOverlayClick"
    >
      <div 
        class="dialog-container" 
        @click.stop=""
      >
        <!-- 图标 -->
        <div 
          class="dialog-icon" 
          :class="[type, variant]"
          v-if="type !== 'prompt'"
        >
          <span v-if="type === 'confirm'">❓</span>
          <span v-else-if="type === 'alert' && variant === 'error'">⚠️</span>
          <span v-else-if="type === 'alert' && variant === 'success'">✅</span>
          <span v-else>ℹ️</span>
        </div>

        <h3 class="dialog-title">{{ title }}</h3>
        <p class="dialog-content" v-if="content">{{ content }}</p>

        <div class="dialog-input-wrapper" v-if="type === 'prompt'">
          <input 
            ref="inputRef"
            v-model="inputValue"
            :placeholder="inputPlaceholder"
            class="dialog-input"
            @keyup.enter.stop="handleConfirm"
            @click.stop
          />
        </div>

        <div class="dialog-actions">
          <button 
            v-if="type !== 'alert'"
            class="btn btn-cancel"
            @click="handleCancel"
          >
            {{ cancelText }}
          </button>
          <button 
            class="btn btn-confirm"
            :class="variant"
            @click="handleConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  visible: Boolean,
  type: { type: String, default: 'confirm' },
  variant: { type: String, default: 'info' },
  title: { type: String, default: '提示' },
  content: { type: String, default: '' },
  inputPlaceholder: { type: String, default: '请输入' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  defaultValue: { type: String, default: '' },
  closeOnOverlay: { type: Boolean, default: true }
})

const emit = defineEmits(['confirm', 'cancel', 'close'])

const inputValue = ref('')
const inputRef = ref(null)

watch(() => props.visible, async (val) => {
  if (val) {
    inputValue.value = props.defaultValue
    if (props.type === 'prompt') {
      await nextTick()
      inputRef.value?.focus()
      inputRef.value?.select()
    }
  }
})

const handleOverlayClick = () => {
  if (props.closeOnOverlay) {
    handleCancel()
  }
}

const handleConfirm = (e) => {
  e?.stopPropagation?.()
  console.log('[DialogProvider] Confirm button clicked')
  emit('confirm', props.type === 'prompt' ? inputValue.value : true)
  emit('close')
}

const handleCancel = (e) => {
  e?.stopPropagation?.()
  console.log('[DialogProvider] Cancel button clicked')
  emit('cancel')
  emit('close')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.dialog-container {
  background: white;
  border-radius: 12px;
  padding: 24px;
  min-width: 320px;
  max-width: 90%;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.dialog-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.dialog-icon.confirm {
  background: #e6f7ff;
  color: #1890ff;
}

.dialog-icon.alert.info {
  background: #f0f9ff;
  color: #1890ff;
}

.dialog-icon.alert.success {
  background: #f6ffed;
  color: #52c41a;
}

.dialog-icon.alert.error {
  background: #fff1f0;
  color: #ff4d4f;
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  text-align: center;
  margin-bottom: 12px;
}

.dialog-content {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 20px;
  line-height: 1.5;
}

.dialog-input-wrapper {
  margin-bottom: 20px;
}

.dialog-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s ease;
}

.dialog-input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 80px;
  user-select: none;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.btn-confirm {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
}

.btn-confirm.success {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
}

.btn-confirm.error {
  background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%);
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background: #e8e8e8;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>