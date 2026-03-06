import { ref, nextTick } from 'vue'

export function useCanvasEvents(baseContainerSize, selectedColor, labelColorMap, store, transformer, layer, annotations, currentLabel) {
  const isDrawing = ref(false)
  const drawingRect = ref(null)
  const dragTick = ref(0)
  const isTransforming = ref(false)
  const startX = ref(0)
  const startY = ref(0)
  
  const isPanning = ref(false)
  const panStartX = ref(0)
  const panStartY = ref(0)
  const stageX = ref(0)
  const stageY = ref(0)
  
  const isSpacePressed = ref(false)

  const resetDrawingState = () => {
    isDrawing.value = false
    drawingRect.value = null
    startX.value = 0
    startY.value = 0
  }

  const handleMouseDown = (e) => {
    if (isTransforming.value) return
    
    const stage = e.target.getStage()
    const isMiddleClick = e.evt && e.evt.button === 1
    const isBackgroundClick = e.target === stage || e.target.attrs?.name === 'background-image'
    
    if ((isSpacePressed.value || isMiddleClick) && isBackgroundClick) {
      isPanning.value = true
      const pos = stage.getPointerPosition()
      if (!pos) return
      
      panStartX.value = pos.x
      panStartY.value = pos.y
      
      stage.container().style.cursor = 'grabbing'
      return
    }
    
    if (isSpacePressed.value) return
    
    const targetName = e.target?.attrs?.name || ''
    if (targetName.startsWith('rect-') || targetName.startsWith('text-')) return
    
    const pos = stage.getPointerPosition()
    if (!pos) return
    
    // ✅ 获取当前的 zoomScale（从外部传入或计算）
    const stageWidth = stage.width()
    const baseWidth = baseContainerSize.value.width
    const zoomScale = stageWidth / baseWidth
    
    // 将屏幕坐标转换为原始坐标
    const { scale: baseScale } = baseContainerSize.value
    
    startX.value = (pos.x / zoomScale - stageX.value) / baseScale
    startY.value = (pos.y / zoomScale - stageY.value) / baseScale
    
    isDrawing.value = true
    drawingRect.value = { 
      x: startX.value, 
      y: startY.value, 
      width: 0, 
      height: 0 
    }
  }

  const handleMouseMove = (e) => {
    if (isPanning.value) {
      const stage = e.target.getStage()
      const pos = stage.getPointerPosition()
      if (!pos) return
      
      const deltaX = pos.x - panStartX.value
      const deltaY = pos.y - panStartY.value
      
      // ✅ 直接修改 stageX/stageY（屏幕坐标变化除以 zoomScale）
      const stageWidth = stage.width()
      const baseWidth = baseContainerSize.value.width
      const zoomScale = stageWidth / baseWidth
      
      stageX.value += deltaX / zoomScale
      stageY.value += deltaY / zoomScale
      
      panStartX.value = pos.x
      panStartY.value = pos.y
      
      dragTick.value++
      return
    }
    
    if (!isDrawing.value) return
    
    if (isTransforming.value) {
      resetDrawingState()
      return
    }
    
    const stage = e.target.getStage()
    const pos = stage.getPointerPosition()
    if (!pos) return
    
    const stageWidth = stage.width()
    const baseWidth = baseContainerSize.value.width
    const zoomScale = stageWidth / baseWidth
    
    const { scale: baseScale } = baseContainerSize.value
    
    const currentX = (pos.x / zoomScale - stageX.value) / baseScale
    const currentY = (pos.y / zoomScale - stageY.value) / baseScale
    
    drawingRect.value = {
      x: Math.min(startX.value, currentX),
      y: Math.min(startY.value, currentY),
      width: Math.abs(currentX - startX.value),
      height: Math.abs(currentY - startY.value)
    }
  }

  const handleMouseUp = (currentLabel, onAnnotationCreated) => {
    return (e) => {
      if (isPanning.value) {
        isPanning.value = false
        const stage = e.target?.getStage()
        if (stage) {
          stage.container().style.cursor = isSpacePressed.value ? 'grab' : 'default'
        }
        return
      }
      
      if (!isDrawing.value) return
      
      try {
        if (drawingRect.value?.width > 5 && drawingRect.value?.height > 5) {
          const newId = `manual_${Date.now()}`
          const finalColor = labelColorMap.get(currentLabel) || selectedColor.value
          
          if (!labelColorMap.has(currentLabel)) {
            labelColorMap.set(currentLabel, finalColor)
          }
          
          // ✅ drawingRect 中已经是原始坐标，直接使用
          const newAnnotation = {
            id: newId,
            x: drawingRect.value.x,
            y: drawingRect.value.y,
            width: drawingRect.value.width,
            height: drawingRect.value.height,
            label: currentLabel,
            color: finalColor
          }
          
          store.addAnnotation(newAnnotation)
          store.selectedId = newId
          
          if (onAnnotationCreated) {
            onAnnotationCreated(newAnnotation)
          }
        }
      } finally {
        resetDrawingState()
      }
    }
  }

  const handleStageClick = (e) => {
    const target = e.target
    const targetName = target?.attrs?.name || ''
    
    if (target === target.getStage() || targetName === 'background-image') {
      store.selectedId = null
      if (transformer.value) {
        const tr = transformer.value.getNode()
        tr.nodes([])
        tr.forceUpdate()
      }
      if (layer.value) {
        layer.value.getNode().batchDraw()
      }
    }
  }

  const selectAnnotation = (e, id) => {
    e.cancelBubble = true
    
    if (e.evt) {
      e.evt.stopPropagation()
    }
    
    if (isTransforming.value) return
    
    store.selectedId = id
    
    const ann = annotations.value.find(a => a.id === id)
    if (ann) {
      currentLabel.value = ann.label
      selectedColor.value = labelColorMap.get(ann.label) || ann.color || '#ff0000'
    }
    
    const rectNode = e.target
    const tr = transformer.value?.getNode()
    
    if (!tr) return
    
    tr.nodes([rectNode])
    tr.forceUpdate()
    rectNode.getLayer().batchDraw()
  }

  const deleteAnnotation = (selectedId) => {
    if (!selectedId) {
      console.warn('⚠️ 没有选中任何标注')
      return
    }
    
    if (confirm('确定删除该标注吗？')) {
      store.deleteAnnotation(selectedId)
      store.selectedId = null
      if (transformer.value) {
        transformer.value.getNode().nodes([])
      }
    }
  }

  const handleRectDragMove = () => {
    dragTick.value++
  }

  const handleRectDragEnd = (e, id) => {
    e.cancelBubble = true
    if (e.evt) e.evt.stopPropagation()
    
    const node = e.target
    const stage = node.getStage()
    
    const stageWidth = stage.width()
    const baseWidth = baseContainerSize.value.width
    const zoomScale = stageWidth / baseWidth
    
    const { scale: baseScale } = baseContainerSize.value
    
    // ✅ node.x() 是屏幕坐标，需要转换回原始坐标
    const newX = (node.x() / zoomScale - stageX.value) / baseScale
    const newY = (node.y() / zoomScale - stageY.value) / baseScale
    
    const ann = annotations.value.find(a => a.id === id)
    if (!ann) return
    
    store.updateAnnotation(id, {
      x: newX,
      y: newY,
      width: ann.width,
      height: ann.height
    })
    
    // ✅ 强制刷新节点位置
    node.x((newX * baseScale + stageX.value) * zoomScale)
    node.y((newY * baseScale + stageY.value) * zoomScale)
    node.scaleX(1)
    node.scaleY(1)
    
    dragTick.value++
  }

  const handleTransformStart = () => {
    isTransforming.value = true
    resetDrawingState()
  }

  const handleTransformEnd = (e, selectedId) => {
    isTransforming.value = false
    
    e.cancelBubble = true
    if (e.evt) e.evt.stopPropagation()
    
    const node = e.target
    const stage = node.getStage()
    
    const stageWidth = stage.width()
    const baseWidth = baseContainerSize.value.width
    const zoomScale = stageWidth / baseWidth
    
    const { scale: baseScale } = baseContainerSize.value
    
    const nodeScaleX = node.scaleX()
    const nodeScaleY = node.scaleY()
    
    // 计算实际像素尺寸
    const screenWidth = node.width() * nodeScaleX
    const screenHeight = node.height() * nodeScaleY
    
    // 转换回原始坐标
    const newWidth = screenWidth / zoomScale / baseScale
    const newHeight = screenHeight / zoomScale / baseScale
    
    const newX = (node.x() / zoomScale - stageX.value) / baseScale
    const newY = (node.y() / zoomScale - stageY.value) / baseScale
    
    store.updateAnnotation(selectedId, {
      x: newX,
      y: newY,
      width: newWidth,
      height: newHeight
    })
    
    nextTick(() => {
      // ✅ 强制刷新节点位置和大小
      node.x((newX * baseScale + stageX.value) * zoomScale)
      node.y((newY * baseScale + stageY.value) * zoomScale)
      node.width(newWidth * baseScale * zoomScale)
      node.height(newHeight * baseScale * zoomScale)
      node.scaleX(1)
      node.scaleY(1)
      
      dragTick.value++
      
      if (transformer.value) {
        const tr = transformer.value.getNode()
        tr.forceUpdate()
      }
    })
  }
  
  const resetPan = () => {
    stageX.value = 0
    stageY.value = 0
    dragTick.value++
  }
  
  const setSpacePressed = (pressed) => {
    isSpacePressed.value = pressed
  }

  return {
    isDrawing,
    drawingRect,
    dragTick,
    isTransforming,
    isPanning,
    stageX,
    stageY,
    isSpacePressed,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    selectAnnotation,
    deleteAnnotation,
    handleRectDragMove,
    handleRectDragEnd,
    handleTransformStart,
    handleTransformEnd,
    handleStageClick,
    resetPan,
    setSpacePressed
  }
}