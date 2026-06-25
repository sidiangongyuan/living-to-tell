<script setup lang="ts">
export interface ContextMenuItem {
  key: string
  label: string
  danger?: boolean
  disabled?: boolean
}

defineProps<{
  open: boolean
  x: number
  y: number
  items: ContextMenuItem[]
}>()

defineEmits<{
  close: []
  select: [item: ContextMenuItem]
}>()
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[80]" @mousedown="$emit('close')" @contextmenu.prevent="$emit('close')" />
  <div
    v-if="open"
    class="fixed z-[81] min-w-[148px] rounded-lg border border-stone-200 bg-white p-1.5 shadow-lg shadow-stone-900/12"
    :style="{ left: `${x}px`, top: `${y}px` }"
    data-testid="context-menu"
    @mousedown.stop
    @contextmenu.prevent
  >
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :disabled="item.disabled"
      :class="[
        'block w-full rounded-md px-3 py-2 text-left text-sm font-semibold transition',
        item.danger
          ? 'text-red-600 hover:bg-red-50'
          : 'text-stone-700 hover:bg-stone-100',
        item.disabled ? 'cursor-not-allowed opacity-40' : '',
      ]"
      @click="$emit('select', item)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
