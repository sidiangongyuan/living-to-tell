<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
  body: string
  startLabel: string
  laterLabel: string
  dismissLabel: string
}>()
const emit = defineEmits<{ start: []; later: []; dismiss: [] }>()
</script>

<template>
  <Teleport to="body">
    <section v-if="open" role="dialog" aria-labelledby="tour-invitation-title" aria-live="polite" class="fixed bottom-5 right-5 z-[65] w-[min(380px,calc(100vw-2rem))] rounded-lg border border-stone-200 bg-white p-4 text-stone-900 shadow-2xl" data-testid="tour-invitation">
      <h2 id="tour-invitation-title" class="text-base font-semibold">{{ title }}</h2>
      <p class="mt-2 text-sm leading-6 text-stone-600">{{ body }}</p>
      <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
        <button type="button" class="text-sm font-medium text-stone-500 underline hover:text-stone-800" @click="emit('dismiss')">{{ dismissLabel }}</button>
        <div class="flex gap-2"><button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="emit('later')">{{ laterLabel }}</button><button type="button" class="rounded-md bg-stone-900 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-700" @click="emit('start')">{{ startLabel }}</button></div>
      </div>
    </section>
  </Teleport>
</template>
