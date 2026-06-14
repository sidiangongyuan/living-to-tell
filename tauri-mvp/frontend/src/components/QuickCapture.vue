<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { articlesApi } from '../api/articles'
import { useI18n } from '../i18n'

const show = ref(false)
const title = ref('')
const body = ref('')
const saving = ref(false)
const { t } = useI18n()

const wordCount = ref(0)
const canSave = computed(() => body.value.trim().length > 0 && !saving.value)

watch(body, (newBody) => {
  const trimmed = newBody.trim()
  wordCount.value = trimmed ? trimmed.split(/\s+/).length : 0
})

async function save() {
  if (!body.value.trim()) return

  saving.value = true
  try {
    // Derive title from first line or first few words
    const derivedTitle = title.value.trim() || body.value.trim().split('\n')[0].slice(0, 50) || 'Quick Note'

    await articlesApi.create({
      title: derivedTitle,
      body: body.value,
      tags: ['quick-capture'],
    })

    // Clear and close
    title.value = ''
    body.value = ''
    show.value = false
  } catch (e) {
    console.error('Quick capture save failed:', e)
    alert(t('quickCapture.saveError'))
  } finally {
    saving.value = false
  }
}

function cancel() {
  if (body.value.trim() && !confirm(t('quickCapture.discardConfirm'))) return
  title.value = ''
  body.value = ''
  show.value = false
}

// Listen for global shortcut (will be triggered by Tauri)
window.addEventListener('quick-capture-toggle', () => {
  show.value = !show.value
})

defineExpose({ open: () => show.value = true, close: () => show.value = false })
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="cancel">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-2xl overflow-hidden" @click.stop>
        <!-- Header -->
        <div class="px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold">{{ t('quickCapture.title') }}</h2>
            <button @click="cancel" class="text-white/80 hover:text-white text-2xl leading-none">&times;</button>
          </div>
        </div>

        <!-- Body -->
        <div class="p-6">
          <input
            v-model="title"
            :placeholder="t('quickCapture.titlePlaceholder')"
            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 mb-4"
          />
          <textarea
            v-model="body"
            :placeholder="t('quickCapture.bodyPlaceholder')"
            class="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 resize-none"
            autofocus
          ></textarea>
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div class="text-sm text-gray-500">{{ wordCount }} {{ t('quickCapture.words') }}</div>
          <div class="flex items-center gap-3">
            <button
              @click="cancel"
              class="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            >
              {{ t('quickCapture.cancel') }}
            </button>
            <button
              @click="save"
              :disabled="!canSave"
              class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {{ saving ? t('quickCapture.saving') : t('quickCapture.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
