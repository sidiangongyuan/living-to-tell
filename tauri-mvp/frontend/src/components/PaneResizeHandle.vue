<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
}>(), {
  title: '拖动调整宽度',
})

defineEmits<{
  pointerdown: [event: PointerEvent]
}>()
</script>

<template>
  <button
    type="button"
    class="pane-resize-handle"
    :title="title"
    :aria-label="title"
    @pointerdown="$emit('pointerdown', $event)"
  />
</template>

