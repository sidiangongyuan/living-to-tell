<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { errorMessage } from '../../api/base'
import {
  settingsApi,
  type AiDiscoveredProfile,
  type AiProfile,
  type AiProfileCreate,
} from '../../api/settings'
import { useI18n } from '../../i18n'

type AccessKind = 'api_key' | 'relay' | 'codex' | 'gemini' | 'gemini_cli' | 'opencode' | 'scan'

const { t } = useI18n()
const profiles = ref<AiProfile[]>([])
const defaultProfileId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const checking = ref(false)
const liveTestingIds = ref<string[]>([])
const selectedLiveTestIds = ref<string[]>([])
const expandedProfileIds = ref<string[]>([])

const wizardOpen = ref(false)
const wizardStep = ref<1 | 2 | 3>(1)
const accessKind = ref<AccessKind>('api_key')
const editingProfileId = ref<string | null>(null)
const savedWizardProfile = ref<AiProfile | null>(null)
const saving = ref(false)
const keyInput = ref('')
const advancedOpen = ref(false)
const draft = ref<AiProfileCreate>(emptyDraft())

const scanning = ref(false)
const discovered = ref<AiDiscoveredProfile[]>([])
const scanOpen = ref(false)

const deleteTarget = ref<AiProfile | null>(null)
const replacementProfileId = ref('')
const deleteLocalKey = ref(false)
const deleting = ref(false)

const accessOptions = computed(() => [
  { id: 'api_key' as const, title: t('settings.profileHub.accessApiKey'), help: t('settings.profileHub.accessApiKeyHelp') },
  { id: 'relay' as const, title: t('settings.profileHub.accessRelay'), help: t('settings.profileHub.accessRelayHelp') },
  { id: 'codex' as const, title: t('settings.profileHub.accessCodex'), help: t('settings.profileHub.accessCodexHelp') },
  { id: 'gemini' as const, title: t('settings.profileHub.accessGemini'), help: t('settings.profileHub.accessGeminiHelp') },
  { id: 'gemini_cli' as const, title: t('settings.profileHub.accessGeminiCli'), help: t('settings.profileHub.accessGeminiCliHelp') },
  { id: 'opencode' as const, title: t('settings.profileHub.accessOpenCode'), help: t('settings.profileHub.accessOpenCodeHelp') },
  { id: 'scan' as const, title: t('settings.profileHub.accessScan'), help: t('settings.profileHub.accessScanHelp') },
])

const replacementOptions = computed(() => profiles.value.filter((item) => item.id !== deleteTarget.value?.id && item.enabled))

function emptyDraft(): AiProfileCreate {
  return {
    name: '',
    provider_name: 'openai',
    base_url: null,
    wire_api: 'chat_completions',
    model: '',
    api_key_source: 'env:OPENAI_API_KEY',
    gemini_cli_proxy: null,
    enabled: true,
    source_key: null,
  }
}

function cleanReason(reason: string): string {
  const lowered = (reason || '').toLowerCase()
  if (!reason) return ''
  if (lowered.includes('missing_var') || lowered.includes('missing_key')) return t('settings.profileHub.missingCredential')
  if (lowered.includes('missing_login')) return t('settings.profileHub.missingLogin')
  if (lowered.includes('auth_list_timeout')) return t('settings.profileHub.authTimeout')
  return errorMessage(reason)
}

function accessLabel(profile: AiProfile): string {
  if (profile.provider_name === 'gemini_cli') return t('settings.profileHub.accessGeminiCli')
  if (profile.provider_name === 'opencode') return t('settings.profileHub.accessOpenCode')
  if (profile.provider_name === 'gemini') return t('settings.profileHub.accessGemini')
  if (profile.api_key_source === 'codex') return t('settings.profileHub.accessCodex')
  if (profile.base_url) return t('settings.profileHub.accessRelay')
  return t('settings.profileHub.accessApiKey')
}

function statusLabel(profile: AiProfile): string {
  if (profile.test_status === 'passed') return t('settings.profileHub.statusPassed')
  if (profile.test_status === 'failed') return t('settings.profileHub.statusFailed')
  if (profile.test_status === 'stale') return t('settings.profileHub.statusStale')
  return t('settings.profileHub.statusUntested')
}

function statusClass(profile: AiProfile): string {
  if (profile.test_status === 'passed') return 'bg-emerald-50 text-emerald-700'
  if (profile.test_status === 'failed') return 'bg-red-50 text-red-700'
  if (profile.test_status === 'stale') return 'bg-amber-50 text-amber-800'
  return 'bg-stone-100 text-stone-600'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await settingsApi.listAiProfiles()
    profiles.value = result.profiles
    defaultProfileId.value = result.default_profile_id ?? null
    selectedLiveTestIds.value = selectedLiveTestIds.value.filter((id) => profiles.value.some((item) => item.id === id))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function openCreateWizard() {
  editingProfileId.value = null
  savedWizardProfile.value = null
  accessKind.value = 'api_key'
  wizardStep.value = 1
  draft.value = emptyDraft()
  keyInput.value = ''
  advancedOpen.value = false
  error.value = ''
  notice.value = ''
  wizardOpen.value = true
}

function openEditWizard(profile: AiProfile) {
  editingProfileId.value = profile.id
  savedWizardProfile.value = profile
  accessKind.value = profile.provider_name === 'gemini_cli'
    ? 'gemini_cli'
    : profile.provider_name === 'opencode'
      ? 'opencode'
      : profile.provider_name === 'gemini'
        ? 'gemini'
        : profile.api_key_source === 'codex'
          ? 'codex'
          : profile.base_url
            ? 'relay'
            : 'api_key'
  draft.value = {
    name: profile.name,
    provider_name: profile.provider_name,
    base_url: profile.base_url,
    wire_api: profile.wire_api,
    model: profile.model,
    api_key_source: profile.api_key_source,
    gemini_cli_proxy: profile.gemini_cli_proxy,
    enabled: profile.enabled,
    source_key: profile.source_key,
  }
  keyInput.value = ''
  advancedOpen.value = false
  wizardStep.value = 2
  error.value = ''
  notice.value = ''
  wizardOpen.value = true
}

async function chooseAccess(kind: AccessKind) {
  accessKind.value = kind
  if (kind === 'scan') {
    wizardOpen.value = false
    await scanLocal()
    return
  }
  const next = emptyDraft()
  if (kind === 'api_key') {
    next.name = t('settings.profileHub.openAiDefaultName')
    next.model = 'gpt-4o-mini'
  } else if (kind === 'relay') {
    next.name = t('settings.profileHub.relayDefaultName')
  } else if (kind === 'codex') {
    next.name = 'Codex / OpenAI'
    next.api_key_source = 'codex'
    next.model = 'gpt-5.5'
    next.wire_api = 'responses'
  } else if (kind === 'gemini') {
    next.name = 'Gemini'
    next.provider_name = 'gemini'
    next.api_key_source = 'env:GEMINI_API_KEY'
    next.model = 'gemini-2.5-flash'
    next.wire_api = 'responses'
  } else if (kind === 'gemini_cli') {
    next.name = 'Gemini CLI'
    next.provider_name = 'gemini_cli'
    next.api_key_source = 'gemini-cli'
    next.model = 'gemini-cli-default'
    next.wire_api = 'responses'
  } else if (kind === 'opencode') {
    next.name = 'OpenCode'
    next.provider_name = 'opencode'
    next.api_key_source = 'opencode'
    next.model = 'opencode/deepseek-v4-flash-free'
    next.wire_api = 'responses'
  }
  draft.value = next
  wizardStep.value = 2
}

async function saveWizardProfile() {
  const name = (draft.value.name || '').trim()
  const model = (draft.value.model || '').trim()
  if (!name || !model) {
    error.value = t('settings.profileHub.nameModelRequired')
    return
  }
  saving.value = true
  error.value = ''
  try {
    let apiKeySource = draft.value.api_key_source
    if (keyInput.value.trim()) {
      const saved = await settingsApi.saveLocalAiKey({
        api_key: keyInput.value.trim(),
        provider_name: draft.value.provider_name,
        model,
        profile_id: editingProfileId.value,
        label: name,
      })
      apiKeySource = saved.api_key_source
      keyInput.value = ''
    }
    const payload: AiProfileCreate = {
      ...draft.value,
      name,
      model,
      base_url: ['gemini_cli', 'opencode'].includes(draft.value.provider_name)
        ? null
        : (draft.value.base_url || '').trim() || null,
      api_key_source: apiKeySource,
      wire_api: draft.value.provider_name === 'openai' ? (draft.value.wire_api || 'chat_completions') : 'responses',
      gemini_cli_proxy: draft.value.provider_name === 'gemini_cli'
        ? (draft.value.gemini_cli_proxy || '').trim() || null
        : null,
    }
    const saved = editingProfileId.value
      ? await settingsApi.updateAiProfile(editingProfileId.value, payload)
      : await settingsApi.createAiProfile(payload)
    editingProfileId.value = saved.id
    savedWizardProfile.value = saved
    wizardStep.value = 3
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function testLive(profile: AiProfile) {
  if (liveTestingIds.value.includes(profile.id)) return
  liveTestingIds.value = [...liveTestingIds.value, profile.id]
  error.value = ''
  try {
    const result = await settingsApi.testAiProfileLive(profile.id)
    profiles.value = profiles.value.map((item) => item.id === result.profile.id ? result.profile : item)
    if (savedWizardProfile.value?.id === result.profile.id) savedWizardProfile.value = result.profile
    if (result.test.ok) {
      notice.value = t('settings.profileHub.livePassed')
    } else {
      notice.value = ''
      error.value = result.test.message
    }
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    liveTestingIds.value = liveTestingIds.value.filter((id) => id !== profile.id)
  }
}

async function runSelectedLiveTests() {
  const queue = profiles.value.filter((item) => selectedLiveTestIds.value.includes(item.id) && item.enabled)
  for (const profile of queue) await testLive(profile)
}

async function checkAll() {
  checking.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await settingsApi.checkAiProfiles()
    profiles.value = result.profiles
    defaultProfileId.value = result.default_profile_id ?? null
    notice.value = t('settings.profileHub.localCheckComplete')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    checking.value = false
  }
}

async function setDefault(profile: AiProfile) {
  error.value = ''
  try {
    const result = await settingsApi.setDefaultAiProfile(profile.id)
    profiles.value = result.profiles
    defaultProfileId.value = result.default_profile_id ?? profile.id
    notice.value = t('settings.profileHub.defaultChanged', { name: profile.name })
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function requestDelete(profile: AiProfile) {
  deleteTarget.value = profile
  replacementProfileId.value = replacementOptions.value[0]?.id ?? ''
  deleteLocalKey.value = false
  error.value = ''
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  error.value = ''
  try {
    await settingsApi.deleteAiProfile(deleteTarget.value.id, {
      replacementProfileId: replacementProfileId.value || undefined,
      deleteLocalKey: deleteLocalKey.value,
    })
    deleteTarget.value = null
    await load()
    notice.value = t('settings.profileHub.deleted')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    deleting.value = false
  }
}

async function scanLocal() {
  scanning.value = true
  scanOpen.value = true
  error.value = ''
  try {
    discovered.value = await settingsApi.discoverAiProfiles()
  } catch (e) {
    error.value = errorMessage(e)
    discovered.value = []
  } finally {
    scanning.value = false
  }
}

async function importCandidate(candidate: AiDiscoveredProfile) {
  error.value = ''
  try {
    await settingsApi.importLocalAiProfiles([candidate.source_key], true)
    await load()
    notice.value = t('settings.profileHub.imported', { name: candidate.name })
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function toggleExpanded(profileId: string) {
  expandedProfileIds.value = expandedProfileIds.value.includes(profileId)
    ? expandedProfileIds.value.filter((id) => id !== profileId)
    : [...expandedProfileIds.value, profileId]
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (deleteTarget.value) deleteTarget.value = null
  else if (scanOpen.value) scanOpen.value = false
  else if (wizardOpen.value) wizardOpen.value = false
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void load()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <section data-testid="ai-profile-hub" class="min-w-0">
    <header class="flex flex-wrap items-start justify-between gap-4 border-b border-stone-200 pb-5">
      <div>
        <h2 class="text-lg font-semibold text-stone-900">{{ t('settings.profileHub.title') }}</h2>
        <p class="mt-1 max-w-2xl text-sm leading-6 text-stone-500">{{ t('settings.profileHub.help') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="scanLocal">
          {{ t('settings.profileHub.scan') }}
        </button>
        <button type="button" class="rounded-md bg-stone-900 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-700" @click="openCreateWizard">
          {{ t('settings.profileHub.add') }}
        </button>
      </div>
    </header>

    <div v-if="error" class="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
    <div v-if="notice" class="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{{ notice }}</div>

    <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
      <div class="flex flex-wrap gap-2">
        <button type="button" :disabled="checking || !profiles.length" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-40" @click="checkAll">
          {{ checking ? t('common.loading') : t('settings.profileHub.checkAll') }}
        </button>
        <button type="button" :disabled="!selectedLiveTestIds.length || liveTestingIds.length > 0" class="rounded-md border border-emerald-300 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-40" @click="runSelectedLiveTests">
          {{ t('settings.profileHub.testSelected', { count: selectedLiveTestIds.length }) }}
        </button>
      </div>
      <p class="text-xs leading-5 text-stone-500">{{ t('settings.profileHub.testCostHint') }}</p>
    </div>

    <div v-if="loading" class="py-10 text-center text-sm text-stone-500">{{ t('common.loading') }}</div>
    <div v-else-if="!profiles.length" class="mt-5 border border-dashed border-stone-300 p-8 text-center">
      <p class="text-sm font-medium text-stone-700">{{ t('settings.profileHub.empty') }}</p>
      <p class="mt-2 text-xs leading-5 text-stone-500">{{ t('settings.profileHub.emptyHelp') }}</p>
    </div>
    <div v-else class="divide-y divide-stone-200">
      <article v-for="profile in profiles" :key="profile.id" class="py-4">
        <div class="flex flex-wrap items-start gap-3">
          <label class="mt-1 flex h-8 w-8 items-center justify-center" :aria-label="t('settings.profileHub.selectForTest', { name: profile.name })">
            <input v-model="selectedLiveTestIds" :value="profile.id" type="checkbox" :disabled="!profile.enabled" class="h-4 w-4 rounded border-stone-300" />
          </label>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="font-semibold text-stone-900">{{ profile.name }}</h3>
              <span v-if="profile.is_default" class="rounded-full bg-stone-900 px-2 py-0.5 text-xs font-semibold text-white">{{ t('settings.profileHub.default') }}</span>
              <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusClass(profile)]">{{ statusLabel(profile) }}</span>
              <span v-if="!profile.enabled" class="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-500">{{ t('settings.disabled') }}</span>
            </div>
            <p class="mt-1 text-sm text-stone-600">{{ profile.model }} · {{ accessLabel(profile) }}</p>
            <p v-if="profile.diagnostic_message" class="mt-2 text-xs leading-5 text-red-700">{{ profile.diagnostic_message }}</p>
            <div v-if="expandedProfileIds.includes(profile.id)" class="mt-3 grid gap-2 text-xs text-stone-500 md:grid-cols-2">
              <div>{{ t('settings.provider') }}: {{ profile.provider_name }}</div>
              <div>{{ t('settings.profileHub.transport') }}: {{ profile.wire_api }}</div>
              <div class="break-all">{{ t('settings.baseUrl') }}: {{ profile.base_url || t('settings.profileHub.officialEndpoint') }}</div>
              <div class="break-all">{{ t('settings.credentialSource') }}: {{ profile.api_key_source }}</div>
              <div v-if="profile.last_tested_at">{{ t('settings.profileHub.lastTest') }}: {{ profile.last_tested_at }}</div>
              <div v-if="profile.last_test_elapsed_ms !== null && profile.last_test_elapsed_ms !== undefined">{{ profile.last_test_elapsed_ms }}ms · {{ profile.last_test_transport || '-' }}</div>
            </div>
          </div>
          <div class="flex flex-wrap justify-end gap-2">
            <button v-if="!profile.is_default" type="button" class="rounded-md border border-stone-300 px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50" @click="setDefault(profile)">{{ t('settings.profileHub.setDefault') }}</button>
            <button type="button" :disabled="liveTestingIds.includes(profile.id)" class="rounded-md border border-emerald-300 px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-40" @click="testLive(profile)">{{ liveTestingIds.includes(profile.id) ? t('common.loading') : t('settings.profileHub.testNow') }}</button>
            <button type="button" class="rounded-md border border-stone-300 px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50" @click="toggleExpanded(profile.id)">{{ expandedProfileIds.includes(profile.id) ? t('common.collapse') : t('common.details') }}</button>
            <button type="button" class="rounded-md border border-stone-300 px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50" @click="openEditWizard(profile)">{{ t('common.edit') }}</button>
            <button type="button" class="rounded-md border border-red-200 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50" @click="requestDelete(profile)">{{ t('common.delete') }}</button>
          </div>
        </div>
      </article>
    </div>
  </section>

  <Teleport to="body">
    <div v-if="wizardOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="wizardOpen = false">
      <div role="dialog" aria-modal="true" aria-labelledby="ai-profile-wizard-title" class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-2xl">
        <header class="sticky top-0 z-10 flex items-start justify-between border-b border-stone-200 bg-white px-5 py-4">
          <div>
            <h3 id="ai-profile-wizard-title" class="text-base font-semibold text-stone-900">{{ editingProfileId ? t('settings.profileHub.editTitle') : t('settings.profileHub.wizardTitle') }}</h3>
            <p class="mt-1 text-xs text-stone-500">{{ t('settings.profileHub.step', { current: wizardStep, total: 3 }) }}</p>
          </div>
          <button type="button" class="h-8 w-8 rounded-md text-stone-500 hover:bg-stone-100" :aria-label="t('common.close')" @click="wizardOpen = false">×</button>
        </header>

        <div class="p-5">
          <div v-if="wizardStep === 1" class="grid gap-3 sm:grid-cols-2">
            <button v-for="option in accessOptions" :key="option.id" type="button" class="border border-stone-200 p-4 text-left hover:border-stone-400 hover:bg-stone-50" @click="chooseAccess(option.id)">
              <span class="block text-sm font-semibold text-stone-900">{{ option.title }}</span>
              <span class="mt-1 block text-xs leading-5 text-stone-500">{{ option.help }}</span>
            </button>
          </div>

          <div v-else-if="wizardStep === 2" class="space-y-4">
            <div class="grid gap-4 md:grid-cols-2">
              <label class="block text-sm font-medium text-stone-700">{{ t('settings.aiProfileName') }}
                <input v-model="draft.name" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" />
              </label>
              <label class="block text-sm font-medium text-stone-700">{{ t('settings.model') }}
                <input v-model="draft.model" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" />
              </label>
            </div>
            <label v-if="!['gemini_cli', 'opencode'].includes(draft.provider_name)" class="block text-sm font-medium text-stone-700">{{ t('settings.baseUrl') }}
              <input v-model="draft.base_url" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" :placeholder="accessKind === 'relay' ? 'https://relay.example/v1' : 'https://api.openai.com/v1'" />
            </label>
            <label v-if="!['codex', 'gemini_cli', 'opencode'].includes(accessKind)" class="block text-sm font-medium text-stone-700">API Key
              <input v-model="keyInput" type="password" autocomplete="off" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" :placeholder="editingProfileId ? t('settings.profileHub.keepExistingKey') : t('settings.localApiKeyPlaceholder')" />
              <span class="mt-1 block text-xs leading-5 text-stone-500">{{ t('settings.profileHub.keyStoredLocally') }}</span>
            </label>
            <button type="button" class="text-sm font-medium text-stone-600 underline" @click="advancedOpen = !advancedOpen">{{ advancedOpen ? t('common.collapse') : t('settings.profileHub.advanced') }}</button>
            <div v-if="advancedOpen" class="grid gap-4 border-t border-stone-200 pt-4 md:grid-cols-2">
              <label class="block text-sm font-medium text-stone-700">Provider
                <select v-model="draft.provider_name" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2">
                  <option value="openai">OpenAI compatible</option><option value="gemini">Gemini</option><option value="gemini_cli">Gemini CLI</option><option value="opencode">OpenCode</option>
                </select>
              </label>
              <label class="block text-sm font-medium text-stone-700">Transport
                <select v-model="draft.wire_api" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="chat_completions">Chat Completions</option><option value="responses">Responses</option></select>
              </label>
              <label class="block text-sm font-medium text-stone-700 md:col-span-2">{{ t('settings.credentialSource') }}
                <input v-model="draft.api_key_source" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" />
              </label>
            </div>
            <div class="flex justify-between gap-3 border-t border-stone-200 pt-4">
              <button v-if="!editingProfileId" type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm" @click="wizardStep = 1">{{ t('common.back') }}</button><span v-else></span>
              <button type="button" :disabled="saving" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="saveWizardProfile">{{ saving ? t('common.saving') : t('settings.profileHub.saveContinue') }}</button>
            </div>
          </div>

          <div v-else class="space-y-5">
            <div class="border border-emerald-200 bg-emerald-50 p-4">
              <p class="text-sm font-semibold text-emerald-900">{{ t('settings.profileHub.saved') }}</p>
              <p class="mt-1 text-xs text-emerald-700">{{ savedWizardProfile?.name }} · {{ savedWizardProfile?.model }}</p>
            </div>
            <p class="text-sm leading-6 text-stone-600">{{ t('settings.profileHub.testBeforeUse') }}</p>
            <div class="flex flex-wrap justify-end gap-2">
              <button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm" @click="wizardOpen = false">{{ t('settings.profileHub.finishLater') }}</button>
              <button v-if="savedWizardProfile" type="button" :disabled="liveTestingIds.includes(savedWizardProfile.id)" class="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="testLive(savedWizardProfile)">{{ liveTestingIds.includes(savedWizardProfile.id) ? t('common.loading') : t('settings.profileHub.sendSmallTest') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="scanOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="scanOpen = false">
      <div role="dialog" aria-modal="true" aria-labelledby="ai-profile-scan-title" class="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-2xl">
        <div class="flex items-center justify-between"><h3 id="ai-profile-scan-title" class="font-semibold text-stone-900">{{ t('settings.profileHub.scanTitle') }}</h3><button class="h-8 w-8 rounded-md hover:bg-stone-100" :aria-label="t('common.close')" @click="scanOpen = false">×</button></div>
        <p class="mt-1 text-xs text-stone-500">{{ t('settings.profileHub.scanPrivacy') }}</p>
        <div v-if="scanning" class="py-10 text-center text-sm text-stone-500">{{ t('common.loading') }}</div>
        <div v-else class="mt-4 divide-y divide-stone-200">
          <article v-for="candidate in discovered" :key="candidate.source_key" class="flex items-start justify-between gap-3 py-3">
            <div><h4 class="text-sm font-semibold text-stone-800">{{ candidate.name }}</h4><p class="mt-1 text-xs text-stone-500">{{ candidate.source_label }} · {{ candidate.model }}</p><p v-if="candidate.reason" class="mt-1 text-xs text-amber-700">{{ cleanReason(candidate.reason) }}</p></div>
            <button :disabled="!candidate.available" class="rounded-md border border-stone-300 px-3 py-1.5 text-xs disabled:opacity-40" @click="importCandidate(candidate)">{{ candidate.existing_profile_id ? t('settings.updateProfile') : t('settings.importProfile') }}</button>
          </article>
          <p v-if="!discovered.length" class="py-8 text-center text-sm text-stone-500">{{ t('settings.noDiscoveredProfiles') }}</p>
        </div>
      </div>
    </div>

    <div v-if="deleteTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="deleteTarget = null">
      <div role="dialog" aria-modal="true" aria-labelledby="ai-profile-delete-title" class="w-full max-w-md rounded-lg bg-white p-5 shadow-2xl">
        <h3 id="ai-profile-delete-title" class="font-semibold text-stone-900">{{ t('settings.profileHub.deleteTitle', { name: deleteTarget.name }) }}</h3>
        <p class="mt-2 text-sm leading-6 text-stone-600">{{ t('settings.profileHub.deleteHelp') }}</p>
        <label v-if="deleteTarget.is_default || replacementOptions.length" class="mt-4 block text-sm font-medium text-stone-700">{{ t('settings.profileHub.replacement') }}
          <select v-model="replacementProfileId" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="">{{ t('settings.profileHub.noReplacement') }}</option><option v-for="item in replacementOptions" :key="item.id" :value="item.id">{{ item.name }} · {{ item.model }}</option></select>
        </label>
        <label class="mt-4 flex items-start gap-2 text-sm text-stone-600"><input v-model="deleteLocalKey" type="checkbox" class="mt-1 h-4 w-4 rounded border-stone-300" /><span>{{ t('settings.profileHub.deleteLocalKey') }}</span></label>
        <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('settings.profileHub.deleteLocalKeyHelp') }}</p>
        <div class="mt-5 flex justify-end gap-2"><button class="rounded-md border border-stone-300 px-3 py-2 text-sm" @click="deleteTarget = null">{{ t('common.cancel') }}</button><button :disabled="deleting" class="rounded-md bg-red-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="confirmDelete">{{ deleting ? t('common.loading') : t('common.delete') }}</button></div>
      </div>
    </div>
  </Teleport>
</template>
