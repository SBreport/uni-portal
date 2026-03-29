import { ref, onUnmounted } from 'vue'

/** 단일 패널 리사이즈 (EquipmentView 스타일) */
export function usePanelResize(options: {
  initialRatio?: number
  min?: number
  max?: number
} = {}) {
  const { initialRatio = 0.35, min = 250, max } = options
  const leftWidth = ref(Math.round(window.innerWidth * initialRatio))
  const isResizing = ref(false)

  let cleanup: (() => void) | null = null

  function startResize(e: MouseEvent) {
    if (isResizing.value) return
    isResizing.value = true
    const startX = e.clientX
    const startWidth = leftWidth.value
    const maxW = max ?? window.innerWidth * 0.65

    const onMouseMove = (ev: MouseEvent) => {
      const newWidth = Math.max(min, Math.min(maxW, startWidth + (ev.clientX - startX)))
      if (leftWidth.value !== newWidth) {
        leftWidth.value = newWidth
      }
    }

    const onMouseUp = () => {
      isResizing.value = false
      doCleanup()
    }

    const doCleanup = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      cleanup = null
    }

    cleanup = doCleanup

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  onUnmounted(() => {
    cleanup?.()
  })

  return { leftWidth, isResizing, startResize }
}

/** 다중 컬럼 리사이즈 (BlogView 스타일) */
export function useColumnResize<T extends { width: number; minWidth: number }>(
  columns: { value: T[] },
) {
  const resizing = ref<{ idx: number; startX: number; startW: number } | null>(null)

  let cleanup: (() => void) | null = null

  function startResize(idx: number, e: MouseEvent) {
    e.preventDefault()
    const col = columns.value[idx]
    if (!col || col.width === 0) return
    resizing.value = { idx, startX: e.clientX, startW: col.width }

    const onMove = (ev: MouseEvent) => {
      if (!resizing.value) return
      const targetCol = columns.value[resizing.value.idx]
      if (!targetCol) return
      const newWidth = Math.max(targetCol.minWidth, resizing.value.startW + (ev.clientX - resizing.value.startX))
      if (targetCol.width !== newWidth) {
        targetCol.width = newWidth
      }
    }
    const onUp = () => {
      resizing.value = null
      doCleanup()
    }

    const doCleanup = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      cleanup = null
    }

    cleanup = doCleanup

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  onUnmounted(() => {
    cleanup?.()
  })

  return { resizing, startResize }
}
