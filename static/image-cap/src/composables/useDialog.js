import { ref, h, render, nextTick } from 'vue'
import DialogProvider from '@/components/DialogProvider.vue'

// 创建全局容器（使用 const 确保不会重复声明）
const DIALOG_CONTAINER_ID = 'dialog-container'

// 使用函数内部静态变量避免外部声明问题
const getContainer = () => {
  let container = document.getElementById(DIALOG_CONTAINER_ID)
  if (!container) {
    container = document.createElement('div')
    container.id = DIALOG_CONTAINER_ID
    document.body.appendChild(container)
  }
  return container
}

// 存储实例的 Map（避免重复声明问题）
const dialogState = {
  instance: null,
  container: null,
  lock: false  // 新增：防止并发弹窗
}

const cleanup = () => {
  console.log('[Dialog] Cleanup started')
  
  // 先标记为不可见
  if (dialogState.instance) {
    // 确保组件响应式更新
    dialogState.instance.props.visible = false
    // 触发更新
    if (dialogState.instance.update) {
      dialogState.instance.update()
    }
  }
  
  // 缩短延迟时间，与动画时长相匹配
  setTimeout(() => {
    console.log('[Dialog] Performing final cleanup')
    if (dialogState.container && dialogState.instance) {
      try {
        render(null, dialogState.container)
      } catch (e) {
        console.warn('[Dialog] Cleanup render error:', e)
      }
      dialogState.instance = null
      dialogState.lock = false  // 释放锁
      console.log('[Dialog] Cleanup completed')
    }
  }, 200) // 从300ms缩短到200ms
}

const createDialog = (options) => {
  return new Promise((resolve) => {
    console.log('[Dialog] Creating dialog with options:', options)
    
    // 检查是否已有弹窗正在显示
    if (dialogState.lock) {
      console.warn('[Dialog] 已有弹窗正在显示，阻止新弹窗')
      resolve({ confirmed: false, value: null })
      return
    }
    
    // 确保容器存在
    if (!dialogState.container) {
      dialogState.container = getContainer()
    }
    
    // 标记锁定状态
    dialogState.lock = true
    
    // 卸载之前的实例（如果有）
    if (dialogState.instance) {
      render(null, dialogState.container)
      dialogState.instance = null
    }

    const dialogProps = {
      ...options,
      visible: true,
      // 添加关键帧动画
      key: Date.now() // 确保每次都是新实例
    }

    // 创建虚拟节点
    const vnode = h(DialogProvider, {
      ...dialogProps,
      onConfirm: (value) => {
        console.log('[Dialog] onConfirm event triggered with value:', value)
        resolve({ confirmed: true, value })
        cleanup()
      },
      onCancel: () => {
        console.log('[Dialog] onCancel event triggered')
        resolve({ confirmed: false, value: null })
        cleanup()
      },
      onClose: () => {
        console.log('[Dialog] onClose event triggered')
        cleanup()
      }
    })

    // 渲染组件
    try {
      render(vnode, dialogState.container)
      dialogState.instance = vnode.component
      
      // 强制更新
      nextTick(() => {
        if (dialogState.instance && dialogState.instance.proxy) {
          dialogState.instance.proxy.forceUpdate?.()
        }
      })
      
      console.log('[Dialog] Dialog rendered successfully')
    } catch (e) {
      console.error('[Dialog] Render error:', e)
      dialogState.lock = false
      resolve({ confirmed: false, value: null })
    }
  })
}

// 导出函数保持不变
export const confirmDialog = (options = {}) => {
  return createDialog({
    type: 'confirm',
    title: options.title || '确认操作',
    content: options.content || '确定要执行此操作吗？',
    confirmText: options.confirmText || '确定',
    cancelText: options.cancelText || '取消',
    variant: options.variant || 'info'
  })
}

export const promptDialog = (options = {}) => {
  return createDialog({
    type: 'prompt',
    title: options.title || '请输入',
    content: options.content || '',
    inputPlaceholder: options.placeholder || '请输入内容',
    defaultValue: options.defaultValue || '',
    confirmText: options.confirmText || '确定',
    cancelText: options.cancelText || '取消',
    variant: options.variant || 'info'
  })
}

export const alertDialog = (options = {}) => {
  return createDialog({
    type: 'alert',
    title: options.title || '提示',
    content: options.content || '操作成功',
    confirmText: options.confirmText || '知道了',
    variant: options.variant || 'info'
  })
}