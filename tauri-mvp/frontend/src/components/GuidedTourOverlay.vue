<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface GuidedTourStep {
  id: string
  title: string
  body: string
  target?: string
}

const props = defineProps<{
  open: boolean
  steps: GuidedTourStep[]
  stepIndex: number
  previousLabel: string
  nextLabel: string
  skipLabel: string
  finishLabel: string
  progressLabel: string
}>()

const emit = defineEmits<{
  previous: []
  next: []
  close: []
  finish: []
}>()

const targetRect = ref<DOMRect | null>(null)

const currentStep = computed(() => props.steps[props.stepIndex] ?? null)
const isFirstStep = computed(() => props.stepIndex <= 0)
const isLastStep = computed(() => props.stepIndex >= props.steps.length - 1)

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max))
}

async function updateTargetRect() {
  await nextTick()
  const selector = currentStep.value?.target
  if (!props.open || !selector) {
    targetRect.value = null
    return
  }
  const element = document.querySelector(selector)
  element?.scrollIntoView({ block: 'center', inline: 'nearest' })
  await new Promise((resolve) => window.requestAnimationFrame(resolve))
  targetRect.value = element?.getBoundingClientRect() ?? null
}

const spotlightStyle = computed(() => {
  const rect = targetRect.value
  if (!rect) return {}
  const padding = 8
  return {
    left: `${Math.max(8, rect.left - padding)}px`,
    top: `${Math.max(8, rect.top - padding)}px`,
    width: `${Math.min(window.innerWidth - 16, rect.width + padding * 2)}px`,
    height: `${Math.min(window.innerHeight - 16, rect.height + padding * 2)}px`,
  }
})

const popoverStyle = computed(() => {
  const width = 360
  const margin = 16
  const minTop = 16
  const maxTop = Math.max(minTop, window.innerHeight - 300)
  const rect = targetRect.value
  if (!rect) {
    return {
      left: `${Math.max(16, Math.round((window.innerWidth - width) / 2))}px`,
      top: `${Math.max(24, Math.round(window.innerHeight * 0.18))}px`,
      width: `${Math.min(width, window.innerWidth - 32)}px`,
    }
  }

  if (rect.right + width + margin < window.innerWidth) {
    return {
      left: `${rect.right + margin}px`,
      top: `${clamp(rect.top, minTop, maxTop)}px`,
      width: `${width}px`,
    }
  }
  if (rect.left - width - margin > 0) {
    return {
      left: `${rect.left - width - margin}px`,
      top: `${clamp(rect.top, minTop, maxTop)}px`,
      width: `${width}px`,
    }
  }
  const belowFits = rect.bottom + margin + 260 < window.innerHeight
  return {
    left: `${clamp(rect.left, margin, Math.max(margin, window.innerWidth - width - margin))}px`,
    top: `${belowFits ? rect.bottom + margin : clamp(rect.top - 276, minTop, maxTop)}px`,
    width: `${Math.min(width, window.innerWidth - 32)}px`,
  }
})

function handleViewportChange() {
  void updateTargetRect()
}

onMounted(() => {
  window.addEventListener('resize', handleViewportChange)
  window.addEventListener('scroll', handleViewportChange, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleViewportChange)
  window.removeEventListener('scroll', handleViewportChange, true)
})

watch(
  () => [props.open, props.stepIndex, props.steps.length],
  () => {
    void updateTargetRect()
  },
  { immediate: true }
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && currentStep"
      class="pointer-events-none fixed inset-0 z-[70]"
      data-testid="guided-tour-overlay"
    >
      <div class="absolute inset-0 bg-stone-950/10" />
      <div
        v-if="targetRect"
        class="absolute rounded-2xl border-2 border-amber-300 bg-amber-100/10 shadow-[0_0_0_9999px_rgba(28,25,23,0.12),0_10px_32px_rgba(217,119,6,0.22)]"
        :style="spotlightStyle"
      />
      <section
        class="pointer-events-auto fixed rounded-2xl border border-stone-200 bg-white p-4 text-stone-900 shadow-2xl"
        :style="popoverStyle"
        role="dialog"
        aria-live="polite"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-600">
              {{ progressLabel }}
            </div>
            <h3 class="mt-1 text-base font-semibold leading-6">{{ currentStep.title }}</h3>
          </div>
          <button
            type="button"
            class="rounded-lg px-2 py-1 text-sm font-semibold text-stone-400 hover:bg-stone-100 hover:text-stone-700"
            @click="emit('close')"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p class="mt-3 text-sm leading-6 text-stone-600">{{ currentStep.body }}</p>
        <div class="mt-4 flex items-center justify-between gap-3">
          <button
            type="button"
            class="rounded-xl px-3 py-2 text-sm font-semibold text-stone-500 hover:bg-stone-100"
            @click="emit('close')"
          >
            {{ skipLabel }}
          </button>
          <div class="flex gap-2">
            <button
              type="button"
              class="rounded-xl border border-stone-200 px-3 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-50 disabled:opacity-40"
              :disabled="isFirstStep"
              @click="emit('previous')"
            >
              {{ previousLabel }}
            </button>
            <button
              v-if="!isLastStep"
              type="button"
              class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-700"
              @click="emit('next')"
            >
              {{ nextLabel }}
            </button>
            <button
              v-else
              type="button"
              class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-700"
              @click="emit('finish')"
            >
              {{ finishLabel }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
</template>
