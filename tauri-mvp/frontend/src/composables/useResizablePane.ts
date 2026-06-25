import { computed, onMounted, onUnmounted, ref } from 'vue'

type ResizeEdge = 'start' | 'end'

interface ResizablePaneOptions {
  key: string
  defaultSize: number
  minSize: number
  maxSize: number
  edge?: ResizeEdge
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

export function useResizablePane(options: ResizablePaneOptions) {
  const storageKey = `living_to_tell:pane:${options.key}`
  const size = ref(options.defaultSize)
  const edge = options.edge ?? 'end'
  let dragState: { pointerId: number; startX: number; startSize: number } | null = null

  function clampToBounds(value: number): number {
    return clamp(Math.round(value), options.minSize, options.maxSize)
  }

  function applySize(value: number) {
    size.value = clampToBounds(value)
    try {
      localStorage.setItem(storageKey, String(size.value))
    } catch {
      // Local storage can be unavailable in strict browser modes.
    }
  }

  function startResize(event: PointerEvent) {
    if (event.button !== 0) return
    event.preventDefault()
    dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startSize: size.value,
    }
    document.body.classList.add('pane-resizing')
    window.addEventListener('pointermove', handleResize)
    window.addEventListener('pointerup', stopResize)
    window.addEventListener('pointercancel', stopResize)
  }

  function handleResize(event: PointerEvent) {
    if (!dragState || event.pointerId !== dragState.pointerId) return
    const delta = event.clientX - dragState.startX
    applySize(edge === 'end' ? dragState.startSize + delta : dragState.startSize - delta)
  }

  function stopResize(event?: PointerEvent) {
    if (event && dragState && event.pointerId !== dragState.pointerId) return
    dragState = null
    document.body.classList.remove('pane-resizing')
    window.removeEventListener('pointermove', handleResize)
    window.removeEventListener('pointerup', stopResize)
    window.removeEventListener('pointercancel', stopResize)
  }

  onMounted(() => {
    try {
      const stored = Number.parseInt(localStorage.getItem(storageKey) || '', 10)
      if (Number.isFinite(stored)) size.value = clampToBounds(stored)
    } catch {
      size.value = clampToBounds(options.defaultSize)
    }
  })

  onUnmounted(() => {
    stopResize()
  })

  const paneStyle = computed(() => ({
    width: `${size.value}px`,
  }))

  return {
    size,
    paneStyle,
    startResize,
  }
}

