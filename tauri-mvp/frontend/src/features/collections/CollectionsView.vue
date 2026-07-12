<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import { errorMessage } from '../../api/base'
import { collectionsApi } from '../../api/collections'
import type {
  CollectionAgentAction,
  AuthorPortraitVersion,
  CollectionAgentDraft,
  CollectionAgentDraftBrief,
  CollectionAgentMemory,
  CollectionAgentMode,
  CollectionAgentReference,
  CollectionAgentRun,
  CollectionAgentSession,
  CollectionAgentState,
  CollectionAgentStyleSample,
  CollectionArticle,
  CollectionOutlineItem,
  CollectionOutlineItemInput,
  CollectionProjectType,
  OutlineItemStatus,
  OutlineItemType,
} from '../../api/collections'
import ContextMenu from '../../components/ContextMenu.vue'
import GuidedTourOverlay from '../../components/GuidedTourOverlay.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import { useResizablePane } from '../../composables/useResizablePane'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'
import {
  buildOutlineMarkdown,
  buildOutlineProgressSummary,
  filterOutlineItems,
  type OutlineFilters,
} from './outlineEnhancements'
import {
  articleTitleForId,
  articleTypeForProject,
  boardTabLabel,
  buildManuscriptTree,
  canUseParent,
  collectionProjectType,
  defaultChildType,
  exportTabLabel,
  flattenManuscriptTree,
  labelsForProject,
  projectTypeLabel,
  structureTabLabel,
  typeLabelForProject,
  unplannedArticles,
  type ManuscriptTreeNode,
} from './manuscriptStructure'
import { useCollectionsStore } from './store'

const LAST_SELECTED_COLLECTION_KEY = 'living_to_tell_last_selected_collection_id'
const AGENT_LONG_ANSWER_THRESHOLD = 700
const ROUTE_HIGHLIGHT_MS = 2600

type AgentQuickTaskKind = 'init' | 'health' | 'continuity' | 'next' | 'memory'
type AgentSlashCommand = {
  command: string
  title: string
  subtitle: string
  action: 'task' | 'clear'
  taskKind?: AgentQuickTaskKind
}

const store = useCollectionsStore()
const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()
const settings = useSettingsStore()

const allArticles = ref<Entry[]>([])
const articlePickerOpen = ref(false)
const createDialogOpen = ref(false)
const selectedArticleIds = ref<string[]>([])
const viewMode = ref<'structure' | 'board' | 'export' | 'agent'>('structure')
const collectionSearch = ref('')
const collectionMetaEditing = ref(false)
const collectionActionsOpen = ref(false)
const outlineEditing = ref(false)
const outlineCreateMenuOpen = ref(false)
const structureGuideOpen = ref(false)
const outlineAdvancedOpen = ref(false)
const newTitle = ref('')
const newDescription = ref('')
const newProjectType = ref<CollectionProjectType>('general')
const draftTitle = ref('')
const draftDescription = ref('')
const draftProjectType = ref<CollectionProjectType>('general')
const savingMeta = ref(false)
const dragOutlineItemId = ref<string | null>(null)
const actionError = ref<string | null>(null)
const outlineActionError = ref<string | null>(null)
const outlineSaving = ref(false)
const outlineExporting = ref(false)
const agentState = ref<CollectionAgentState | null>(null)
const agentLoading = ref(false)
const agentError = ref<string | null>(null)
const agentPrompt = ref('')
const agentReferenceQuery = ref('')
const agentReferenceResults = ref<CollectionAgentReference[]>([])
const selectedAgentRefs = ref<CollectionAgentReference[]>([])
const agentReferencePickerOpen = ref(false)
const agentSearchLoading = ref(false)
const agentRunning = ref(false)
const agentRequestWebContext = ref(false)
const agentProfileId = ref('default')
const agentDefaultProfileId = ref('default')
const agentMemoryDraft = ref<Record<string, string>>({})
const agentMemorySaving = ref(false)
const agentApplyingActionId = ref<string | null>(null)
const agentPendingQuickTask = ref<AgentQuickTaskKind | null>(null)
const agentCollapsedRunIds = ref<string[]>([])
const agentExpandedRunIds = ref<string[]>([])
const agentHighlightedRunId = ref<string | null>(null)
const agentPromptIndexQuery = ref('')
const agentSlashMenuOpen = ref(false)
const agentSlashQuery = ref('')
const agentSlashSelectedIndex = ref(0)
const agentClearDialogOpen = ref(false)
const agentClearing = ref(false)
const agentMode = ref<CollectionAgentMode>('discuss')
const agentSessionQuery = ref('')
const agentShowArchivedSessions = ref(false)
const agentCreatingSession = ref(false)
const agentNewSessionTitle = ref('')
const agentSessionBusy = ref(false)
const agentRenamingSession = ref(false)
const agentSessionTitleDraft = ref('')
const agentLeftPanelOpen = ref(typeof window === 'undefined' ? true : window.innerWidth >= 1280)
const agentRightPanelOpen = ref(false)
const agentRightTab = ref<'context' | 'drafts' | 'memory'>('context')
const selectedAgentDraftId = ref<string | null>(null)
const agentDraftTitle = ref('')
const agentDraftContent = ref('')
const agentDraftSaving = ref(false)
const agentDraftApplyOpen = ref(false)
const agentDraftApplyOperation = ref<'create_article' | 'append' | 'replace_selection'>('create_article')
const agentDraftTargetEntryId = ref('')
const agentDraftArticleTitle = ref('')
const agentDraftSelectionText = ref('')
const agentDraftApplying = ref(false)
const agentDraftSelectedIds = ref<string[]>([])
const agentDraftBrief = ref<CollectionAgentDraftBrief>({
  target_scene: '',
  pov: '',
  tense: '',
  target_length: 1200,
  must_happen: [],
  avoid: [],
})
const agentDraftMustHappenText = ref('')
const agentDraftAvoidText = ref('')
const agentStyleSamples = ref<CollectionAgentStyleSample[]>([])
const agentStyleEntryId = ref('')
const agentPortraitTagsText = ref('')
const agentPortraitSummary = ref('')
const agentPortraitSaving = ref(false)
const agentPortraitVersions = ref<AuthorPortraitVersion[]>([])
const agentPortraitHistoryOpen = ref(false)
const highlightedCollectionArticleId = ref<string | null>(null)
const windowWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth)
let agentLoadToken = 0
let agentPollTimer: number | null = null
let agentReferenceSearchToken = 0
let collectionArticleHighlightTimer: number | null = null
let collectionSelectionToken = 0
const outlineDraftTitle = ref('')
const outlineDraftType = ref<OutlineItemType>('scene')
const outlineDraftStatus = ref<OutlineItemStatus>('idea')
const outlineDraftParentId = ref('')
const outlineDraftSummary = ref('')
const outlineDraftNotes = ref('')
const outlineDraftEntryId = ref('')
const outlineDraftPov = ref('')
const outlineDraftSetting = ref('')
const outlineDraftTimeline = ref('')
const outlineDraftTags = ref('')
const outlineDraftTargetWords = ref<number | null>(null)
const outlineFilterType = ref<OutlineFilters['type']>('all')
const outlineFilterStatus = ref<OutlineFilters['status']>('all')
const outlineFilterUnlinkedOnly = ref(false)
const tourOpen = ref(false)
const tourStepIndex = ref(0)

const collectionListPane = useResizablePane({
  key: 'collections:list',
  defaultSize: 240,
  minSize: 240,
  maxSize: 420,
})
const structurePane = useResizablePane({
  key: 'collections:structure',
  defaultSize: 380,
  minSize: 320,
  maxSize: 560,
})

const collectionListPaneStyle = computed(() => ({
  width: windowWidth.value < 1180
    ? `${Math.max(200, Math.min(collectionListPane.size.value, Math.floor(windowWidth.value * 0.22)))}px`
    : `${collectionListPane.size.value}px`,
}))
const structurePaneStyle = computed(() => ({
  width: windowWidth.value < 1280
    ? `${Math.max(280, Math.min(structurePane.size.value, Math.floor(windowWidth.value * 0.3)))}px`
    : `${structurePane.size.value}px`,
}))

const deleteContextMenuOpen = ref(false)
const deleteContextMenuX = ref(0)
const deleteContextMenuY = ref(0)
const deleteContextTarget = ref<{ kind: 'collection'; id: string } | null>(null)

const projectType = computed(() => collectionProjectType(store.selectedCollection))
const projectLabels = computed(() => labelsForProject(projectType.value, locale.value))
const filteredCollections = computed(() => {
  const query = collectionSearch.value.trim().toLowerCase()
  if (!query) return store.collections
  return store.collections.filter((collection) => {
    const haystack = [
      collection.title,
      collection.description,
      projectTypeLabel(collection.project_type, locale.value),
    ].join(' ').toLowerCase()
    return haystack.includes(query)
  })
})
const currentArticleIds = computed(() => new Set(store.articles.map((article) => article.id)))
const outlineProgress = computed(() => buildOutlineProgressSummary(store.outline, store.articles))
const outlineProgressPercent = computed(() => {
  if (!outlineProgress.value.targetWordTotal) return null
  return Math.min(100, Math.round((outlineProgress.value.linkedArticleWordCount / outlineProgress.value.targetWordTotal) * 100))
})
const manuscriptTree = computed(() => buildManuscriptTree(store.outline))
const flatTree = computed(() => flattenManuscriptTree(manuscriptTree.value))
const filteredOutline = computed(() => filterOutlineItems(store.outline, {
  type: outlineFilterType.value,
  status: outlineFilterStatus.value,
  unlinkedOnly: outlineFilterUnlinkedOnly.value,
}))
const unplanned = computed(() => unplannedArticles(store.articles, store.outline))
const hasLinkedStructure = computed(() => store.outline.some((item) => Boolean(item.entry_id)))
const selectedParent = computed(() => {
  const parentId = store.selectedOutlineItem?.parent_id
  return parentId ? store.outline.find((item) => item.id === parentId) ?? null : null
})
const outlineLinkedArticle = computed(() => {
  const entryId = store.selectedOutlineItem?.entry_id
  if (!entryId) return null
  return allArticles.value.find((article) => article.id === entryId)
    ?? store.articles.find((article) => article.id === entryId)
    ?? null
})
const parentOptions = computed(() => {
  const currentId = store.selectedOutlineItemId
  return flatTree.value.filter((node) =>
    !currentId || node.item.id !== currentId && canUseParent(store.outline, currentId, node.item.id)
  )
})
const outlineBoardColumns = computed(() =>
  outlineStatusOptions.value.map((status) => ({
    ...status,
    items: filteredOutline.value.filter((item) => item.status === status.value),
  }))
)
const agentRuns = computed(() => agentState.value?.runs ?? [])
const agentActions = computed(() => agentState.value?.actions ?? [])
const pendingAgentActions = computed(() => agentActions.value.filter((action) => ['pending', 'deferred'].includes(action.status)))
const activeAgentRun = computed(() =>
  agentState.value?.active_run
  ?? agentRuns.value.find((run) => !['succeeded', 'failed', 'cancelled'].includes(run.status))
  ?? null
)
const agentProfileOptions = computed(() => agentState.value?.profiles ?? [{ id: 'default', name: '默认配置' }])
const agentQuickTasks = computed(() => [
  {
    kind: 'init' as const,
    title: locale.value === 'en' ? 'Initialize Agent' : '初始化 Agent',
    subtitle: locale.value === 'en' ? 'Establish a book baseline' : '绑定本书、建立基线',
    prompt: locale.value === 'en'
      ? 'Establish your baseline for this collection: inspect its structure, unplanned articles, and Project Bible; explain what is known, what is missing, and which confirmed memory or structure would help next. Create reviewable proposals only and do not modify manuscript text.'
      : '请初始化你作为当前作品集 Agent 的工作基线：阅读作品集结构、未编排文章和项目圣经，说明你已经掌握了什么、还缺什么、建议作者先补哪些记忆或结构信息。只生成可确认提案，不要改正文。',
  },
  {
    kind: 'health' as const,
    title: locale.value === 'en' ? 'Project Checkup' : '体检作品集',
    subtitle: locale.value === 'en' ? 'Structure, gaps, next move' : '结构、缺口、下一步',
    prompt: locale.value === 'en' ? 'Review this collection for structural clarity, missing chapters or scenes, and the most useful next step. Give evidence and reviewable proposals.' : '请体检这个作品集：结构是否清楚、章节/场景是否缺口明显、下一步最该补什么。请给出证据和可确认提案。',
  },
  {
    kind: 'continuity' as const,
    title: locale.value === 'en' ? 'Continuity Check' : '检查连续性',
    subtitle: locale.value === 'en' ? 'Character, timeline, setup' : '人物、时间线、伏笔',
    prompt: locale.value === 'en' ? 'Check this collection for continuity risks in character motivation, timeline, foreshadowing, and world rules. Point to concrete evidence and next steps.' : '请检查这个作品集的连续性风险：人物动机、时间线、伏笔、设定是否有断裂或未解决问题。请给出具体位置和下一步。',
  },
  {
    kind: 'next' as const,
    title: locale.value === 'en' ? 'Suggest Next Step' : '建议下一步',
    subtitle: locale.value === 'en' ? 'What matters today' : '今天最该推进什么',
    prompt: locale.value === 'en' ? 'Based on the collection structure and confirmed memory, suggest the single most useful step to advance today. Explain the reason, risk, and concrete action.' : '请根据当前作品集结构和项目记忆，建议今天最该推进的一步。请说明理由、风险和可执行动作。',
  },
  {
    kind: 'memory' as const,
    title: locale.value === 'en' ? 'Organize Memory' : '整理项目记忆',
    subtitle: locale.value === 'en' ? 'Propose stable facts only' : '稳定事实先提案',
    prompt: locale.value === 'en' ? 'Organize the current Project Bible. Turn stable facts into memory update proposals and place uncertain ideas under open questions.' : '请整理当前作品集的项目圣经。只把稳定事实做成记忆更新提案，不确定内容放到未解决问题。',
  },
])
const pendingQuickTask = computed(() =>
  agentQuickTasks.value.find((task) => task.kind === agentPendingQuickTask.value) ?? null
)
const agentSlashCommands = computed<AgentSlashCommand[]>(() => [
  ...agentQuickTasks.value.map((task) => ({
    command: task.kind,
    title: task.title,
    subtitle: task.subtitle,
    action: 'task' as const,
    taskKind: task.kind,
  })),
  {
    command: 'clear',
    title: locale.value === 'en' ? 'Clear Conversation' : '清空会话',
    subtitle: locale.value === 'en' ? 'Keep canon, drafts, and open proposals' : '保留项目圣经和待确认提案',
    action: 'clear',
  },
])
const filteredAgentSlashCommands = computed(() => {
  const query = agentSlashQuery.value.trim().toLowerCase()
  if (!query) return agentSlashCommands.value
  return agentSlashCommands.value.filter((command) =>
    command.command.includes(query)
    || command.title.toLowerCase().includes(query)
    || command.subtitle.toLowerCase().includes(query)
  )
})
const selectedAgentProfileName = computed(() =>
  agentProfileOptions.value.find((profile) => profile.id === agentProfileId.value)?.name
  || (locale.value === 'en' ? 'Current profile' : '当前配置')
)
const filteredAgentPromptIndex = computed(() => {
  const query = agentPromptIndexQuery.value.trim().toLowerCase()
  return agentRuns.value.filter((run) => {
    const text = agentRunMessage(run)
    if (!query) return true
    return text.toLowerCase().includes(query) || agentRunTaskLabel(run).toLowerCase().includes(query)
  })
})
const activeAgentSession = computed(() =>
  agentState.value?.sessions.find((session) => session.id === agentState.value?.active_session_id) ?? null
)
const filteredAgentSessions = computed(() => {
  const query = agentSessionQuery.value.trim().toLowerCase()
  return (agentState.value?.sessions ?? []).filter((session) => {
    if (!agentShowArchivedSessions.value && session.archived) return false
    if (!query) return true
    return `${session.title} ${session.summary}`.toLowerCase().includes(query)
  })
})
const currentAgentDrafts = computed(() =>
  (agentState.value?.drafts ?? []).filter((draft) => draft.session_id === agentState.value?.active_session_id)
)
const unappliedAgentDrafts = computed(() =>
  (agentState.value?.drafts ?? []).filter((draft) => draft.status === 'draft')
)
const selectedAgentDraft = computed(() =>
  (agentState.value?.drafts ?? []).find((draft) => draft.id === selectedAgentDraftId.value) ?? null
)
const activeStyleSample = computed(() =>
  agentStyleSamples.value.find((sample) => sample.status === 'active') ?? null
)
const agentModeOptions = computed<Array<{ value: CollectionAgentMode; label: string; help: string }>>(() => (
  locale.value === 'en'
    ? [
        { value: 'discuss', label: 'Discuss', help: 'Explore ideas without forcing a decision' },
        { value: 'plan', label: 'Plan', help: 'Turn decisions into structure and next steps' },
        { value: 'draft', label: 'Draft', help: 'Create an unapplied scene draft' },
        { value: 'review', label: 'Review', help: 'Check continuity, logic, and pacing' },
      ]
    : [
        { value: 'discuss', label: '讨论', help: '一起构思，不急着替你定案' },
        { value: 'plan', label: '规划', help: '把决定整理成结构与下一步' },
        { value: 'draft', label: '草稿', help: '生成一份尚未写入正文的场景稿' },
        { value: 'review', label: '审校', help: '检查连续性、逻辑与节奏' },
      ]
))
const agentCopy = computed(() => locale.value === 'en' ? {
  workspace: 'Coauthor Workspace', newSession: 'New session', sessionName: 'Session name', searchSessions: 'Search sessions',
  sessions: 'Sessions', archived: 'Archived', messages: 'messages', draftsCount: 'drafts', currentPrompts: 'This session', clear: 'Clear',
  searchPrompts: 'Find my prompts', showArchived: 'Show archived', renameSession: 'Rename session', archiveSession: 'Archive session', deleteSession: 'Delete session',
  defaultSession: 'Coauthoring', nextProfile: 'AI profile for this run', sessionsToggle: 'Sessions', sessionsHelp: 'Show sessions and your prompt index', resources: 'Workspace', resourcesHelp: 'Open context, drafts, proposals, and Project Bible', running: 'Agent is working', otherSession: 'from another session', interrupt: 'Interrupt',
  zeroTitle: 'Start with an unfinished idea', zeroBody: 'Discuss freely or ask for several directions first. Conversation does not become canon until you accept a proposal.',
  zeroIdea: 'Explore from zero', character: 'Discuss a character', structure: 'Shape the structure', waiting: 'Waiting for a reply...',
  authorDecision: 'Author confirmation', openDraft: 'Open saved draft', canonConflict: 'Canon conflict · author decides', existingCanon: 'Project Bible', proposedCanon: 'This run',
  apply: 'Apply', defer: 'Later', reject: 'Reject', prepare: 'Ready to run', uses: 'Using', confirm: 'Confirm', cancel: 'Cancel',
  sceneBrief: 'Scene brief', sceneBriefHelp: 'Constrains this draft only; never writes to the manuscript', targetScene: 'Target scene', pov: 'POV', tense: 'Tense', length: 'Words', must: 'Must happen, one per line', avoid: 'Avoid, one per line',
  addReference: 'Add reference', searchReferences: 'Search structure, articles, cards, motifs, or references', collapse: 'Close', searching: 'Searching...', noReferences: 'No matching references',
  discussPlaceholder: 'Discuss with Agent; use @ for context or / for actions', draftPlaceholder: 'Describe the scene; use @ to add context', web: 'Ask for web access', send: 'Send', generate: 'Generate draft', starting: 'Starting...',
  contextTab: 'Context', draftsTab: 'Drafts', memoryTab: 'Memory', readTitle: 'What this run can read', readHelp: 'Structure index, Project Bible, session summary, recent six turns, and explicit references. Never the whole manuscript by default.', refresh: 'Refresh',
  collectionDefault: 'Collection default model', nextOverride: 'The top selector overrides one run only', projectBible: 'Project Bible', recentChat: 'Recent chat', explicitRefs: 'Explicit refs', wholeBook: 'Whole manuscript', included: 'Included', maxSix: 'Up to 6 turns', notRead: 'Not read', addRunRef: 'Add reference for this run',
  proposals: 'Open proposals', noProposals: 'No open proposals. Normal chat never writes data automatically.', viewChange: 'View change', deferred: 'deferred',
  draftLibrary: 'Draft Library', draftLibraryHelp: 'Stored locally and excluded from articles, search, and export until applied.', deleteSelected: 'Delete selected', clearUnapplied: 'Clear unapplied', emptyDrafts: 'Switch to Draft, add a light scene brief, and generate the first candidate.', applied: 'Applied', primaryDraft: 'Primary draft', saveChanges: 'Save changes', saving: 'Saving...', writeArticle: 'Write to article...', variant: 'Generate variant', deleteDraft: 'Delete draft', appliedHelp: 'Applied to an article. This record remains traceable and can no longer be edited.',
  portrait: 'Author Portrait', portraitHelp: 'Reusable across books and based only on author-confirmed writing cycles.', history: 'History', portraitTags: 'Style tags, separated by commas', portraitSummary: 'Describe stable writing tendencies in your own words', cycles: 'completed cycles', savePortrait: 'Save portrait', portraitReminder: 'Three new full writing cycles are ready for an evidence-based portrait proposal. No model runs automatically.', proposePortrait: 'Generate proposal',
  styleCycles: 'Writing evidence cycles', styleCyclesHelp: 'Capture the author draft first; after discussion and revision, mark the chapter complete.', inProgress: 'In progress', article: 'Article', completeChapter: 'Mark chapter complete', chooseArticle: 'Choose article', start: 'Start', save: 'Save', memoryRule: 'Normal chat and rejected proposals never enter long-term memory. Clearing a session does not delete the Project Bible.',
  newSessionTitle: 'New coauthor session', newSessionHelp: 'Sessions keep separate conversations and drafts while sharing this book\'s Project Bible.', sessionExample: 'For example: Act One exploration', creating: 'Creating...', create: 'Create',
  draftApplyTitle: 'Write draft to article', draftApplyHelp: 'Review the destination first. Append and replace create a version snapshot automatically.', articleTitle: 'Article title', targetArticle: 'Target article', uniqueSelection: 'Paste the one exact passage to replace', writePreview: 'Write preview', applying: 'Applying...', confirmWrite: 'Confirm write',
  portraitVersions: 'Author Portrait versions', noPortraitVersions: 'No restorable versions yet.', noTags: 'No tags', emptyPortrait: 'Empty portrait', restore: 'Restore',
  clearTitle: 'Clear this Agent session?', clearHelp: 'Clears this session\'s messages, terminal runs, and handled proposals. Other sessions, the Draft Library, Project Bible, articles, outline, applied data, and open proposals stay intact.', clearMemoryHelp: 'Normal conversation never enters long-term memory automatically. Only saving the Project Bible or applying a memory update proposal writes memory.', clearing: 'Clearing...', confirmClear: 'Confirm clear',
  deleteSessionConfirm: 'Delete this session and its unapplied drafts? The Project Bible, applied articles, and other sessions will stay intact.', close: 'Close', freeChat: 'Conversation', emptyTask: 'Empty task', expandAnswer: 'Expand full answer', collapseAnswer: 'Collapse long answer',
  sessionSummary: 'Working summary', rebuildSummary: 'Rebuild', sessionSummaryHelp: 'A working summary, not canon. Raw messages are retained.', appliedStatus: 'Applied', rejectedStatus: 'Rejected', deferredStatus: 'Later',
} : {
  workspace: '共创工作台', newSession: '新建会话', sessionName: '会话名称', searchSessions: '搜索会话',
  sessions: '会话', archived: '归档', messages: '条消息', draftsCount: '份草稿', currentPrompts: '本会话 Prompt', clear: '清空',
  searchPrompts: '查找我问过的问题', showArchived: '显示已归档', renameSession: '重命名当前会话', archiveSession: '归档当前会话', deleteSession: '删除当前会话',
  defaultSession: '共同构思', nextProfile: '本轮 AI 配置', sessionsToggle: '会话', sessionsHelp: '显示会话列表和 Prompt 索引', resources: '工作栏', resourcesHelp: '打开上下文、草稿、提案和项目圣经', running: 'Agent 正在工作', otherSession: '来自另一会话', interrupt: '中断',
  zeroTitle: '从一句还没成形的想法开始', zeroBody: '你可以自由讨论，也可以让 Agent 先给几个方向。对话不会自动变成设定，只有确认的提案才进入项目圣经。',
  zeroIdea: '从零构思', character: '讨论人物', structure: '整理结构', waiting: '等待回答...',
  authorDecision: '待作者确认', openDraft: '查看已保存草稿', canonConflict: 'Canon 冲突 · 由作者决定', existingCanon: '项目圣经现有', proposedCanon: '本轮提出',
  apply: '应用', defer: '稍后', reject: '拒绝', prepare: '准备运行', uses: '使用', confirm: '确认', cancel: '取消',
  sceneBrief: '场景简报', sceneBriefHelp: '只约束本轮草稿，不写入正文', targetScene: '目标场景，例如：雨夜收到旧信', pov: '视角', tense: '时态', length: '字数', must: '必须发生，每行一项', avoid: '避免什么，每行一项',
  addReference: '引用', searchReferences: '搜索结构、文章、卡片、意象或文脉', collapse: '收起', searching: '搜索中...', noReferences: '没有匹配引用',
  discussPlaceholder: '和 Agent 讨论；输入 @ 加引用，输入 / 打开功能', draftPlaceholder: '描述这一场要写什么；输入 @ 添加上下文', web: '联网请求', send: '发送', generate: '生成草稿', starting: '启动中...',
  contextTab: '上下文', draftsTab: '草稿', memoryTab: '记忆', readTitle: '本轮会读什么', readHelp: '默认读取结构索引、项目圣经、会话摘要和最近六轮，不会偷读整本正文。', refresh: '刷新',
  collectionDefault: '作品集默认模型', nextOverride: '顶部选择只覆盖下一轮', projectBible: '项目圣经', recentChat: '最近对话', explicitRefs: '显式引用', wholeBook: '整本正文', included: '已加入', maxSix: '最多 6 轮', notRead: '不读取', addRunRef: '添加本轮引用',
  proposals: '待确认提案', noProposals: '没有待处理提案。普通聊天不会自动写入数据。', viewChange: '查看变更', deferred: '稍后处理',
  draftLibrary: '草稿库', draftLibraryHelp: '草稿保存在本机，应用前不会进入文章、搜索或导出。', deleteSelected: '删除所选', clearUnapplied: '清空未应用', emptyDrafts: '切到“草稿”模式，填写轻量场景简报后生成第一份候选稿。', applied: '已应用', primaryDraft: '主草稿', saveChanges: '保存修改', saving: '保存中...', writeArticle: '写入文章...', variant: '生成变体', deleteDraft: '删除草稿', appliedHelp: '已应用到文章。保留此记录用于追溯，不再允许修改。',
  portrait: '作者画像', portraitHelp: '跨作品复用，但只依据你确认过的写作闭环样本。', history: '历史', portraitTags: '风格标签，用逗号分隔', portraitSummary: '用自己的话描述稳定写作倾向', cycles: '个已完成闭环', savePortrait: '保存画像', portraitReminder: '已有 3 个新的完整写作闭环，可以让 Agent 基于证据提出画像更新。不会自动调用模型。', proposePortrait: '生成更新提案',
  styleCycles: '写作闭环样本', styleCyclesHelp: '开始时记录作者原稿；讨论、修改并确认章节完成后，再记录最终稿。', inProgress: '进行中', article: '文章', completeChapter: '标记章节完成', chooseArticle: '选择文章', start: '开始', save: '保存', memoryRule: '普通对话和被拒绝的提案不会进入长期记忆。清空会话也不会删除项目圣经。',
  newSessionTitle: '新建共创会话', newSessionHelp: '不同会话有各自的对话与草稿，但共享这本书的项目圣经。', sessionExample: '例如：第一幕构思', creating: '创建中...', create: '创建',
  draftApplyTitle: '将草稿写入文章', draftApplyHelp: '应用前会预览目标；追加或替换会自动创建版本快照。', articleTitle: '文章标题', targetArticle: '目标文章', uniqueSelection: '粘贴要替换的唯一原文', writePreview: '写入预览', applying: '应用中...', confirmWrite: '确认写入',
  portraitVersions: '作者画像版本', noPortraitVersions: '还没有可恢复的历史版本。', noTags: '无标签', emptyPortrait: '空画像', restore: '恢复',
  clearTitle: '清空 Agent 会话？', clearHelp: '这会清掉当前会话的对话消息、已结束任务和已处理提案记录；其他会话、草稿库、项目圣经、文章、大纲、已应用数据，以及仍待确认的提案都会保留。', clearMemoryHelp: '普通对话不会自动进入长期记忆。只有手动保存项目圣经，或应用“更新记忆”提案，才会写入长期记忆。', clearing: '清空中...', confirmClear: '确认清空',
  deleteSessionConfirm: '删除当前会话及其未应用草稿？项目圣经、已应用文章和其他会话不会删除。', close: '关闭', freeChat: '普通对话', emptyTask: '空任务', expandAnswer: '展开完整回答', collapseAnswer: '收起长回答',
  sessionSummary: '会话工作摘要', rebuildSummary: '重新整理', sessionSummaryHelp: '这是工作摘要，不是 canon；原消息仍保留。', appliedStatus: '已应用', rejectedStatus: '已拒绝', deferredStatus: '稍后处理',
})
const currentAgentMode = computed(() =>
  agentModeOptions.value.find((item) => item.value === agentMode.value) ?? agentModeOptions.value[0]
)
const agentRightTabs = computed<Array<{ id: 'context' | 'drafts' | 'memory'; label: string }>>(() => [
  { id: 'context', label: agentCopy.value.contextTab },
  { id: 'drafts', label: `${agentCopy.value.draftsTab} ${unappliedAgentDrafts.value.length || ''}`.trim() },
  { id: 'memory', label: agentCopy.value.memoryTab },
])
const agentDraftApplyOptions = computed<Array<{ id: 'create_article' | 'append' | 'replace_selection'; label: string }>>(() => locale.value === 'en'
  ? [{ id: 'create_article', label: 'New article' }, { id: 'append', label: 'Append' }, { id: 'replace_selection', label: 'Replace selection' }]
  : [{ id: 'create_article', label: '新建文章' }, { id: 'append', label: '追加' }, { id: 'replace_selection', label: '替换选区' }])
const latestAgentContextManifest = computed<Record<string, unknown> | null>(() => {
  const run = agentRuns.value.find((item) => item.status === 'succeeded' && item.result?.context_manifest)
  return (run?.result?.context_manifest as Record<string, unknown> | undefined) ?? null
})
const latestAgentContextLabel = computed(() => {
  const manifest = latestAgentContextManifest.value
  if (!manifest) return ''
  const refs = Array.isArray(manifest.explicit_refs) ? manifest.explicit_refs.length : 0
  const turns = Number(manifest.recent_turns || 0)
  return locale.value === 'en'
    ? `Last run used ${turns} recent turns and ${refs} explicit references; it did not read the whole manuscript.`
    : `最近一轮实际使用：${turns} 轮对话、${refs} 个显式引用；整本正文未读取。`
})

const projectTypeOptions = computed(() => ([
  { value: 'general' as const, label: projectTypeLabel('general', locale.value) },
  { value: 'novel' as const, label: projectTypeLabel('novel', locale.value) },
  { value: 'essay' as const, label: projectTypeLabel('essay', locale.value) },
  { value: 'nonfiction' as const, label: projectTypeLabel('nonfiction', locale.value) },
]))
const outlineTypeOptions = computed(() => ([
  { value: 'part' as const, label: projectLabels.value.part },
  { value: 'chapter' as const, label: projectLabels.value.chapter },
  { value: 'scene' as const, label: projectLabels.value.scene },
  { value: 'note' as const, label: projectLabels.value.note },
]))
const outlineStatusOptions = computed(() => ([
  { value: 'idea' as const, label: t('collectionOutline.statusIdea') },
  { value: 'drafting' as const, label: t('collectionOutline.statusDrafting') },
  { value: 'revising' as const, label: t('collectionOutline.statusRevising') },
  { value: 'done' as const, label: t('collectionOutline.statusDone') },
  { value: 'parked' as const, label: t('collectionOutline.statusParked') },
]))
const outlineTypeGuide = computed(() => {
  if (locale.value === 'en') {
    if (projectType.value === 'novel') {
      return 'Novel structure usually reads Part -> Chapter -> Scene. A part is a large act or volume, a chapter is what readers see in the table of contents, a scene is one concrete beat or draft slot, and a note is planning-only.'
    }
    if (projectType.value === 'essay') {
      return 'Essay collections usually read Section -> Group -> Essay. A section is a large theme, a group gathers related essays, an essay is a real piece, and a note is planning-only.'
    }
    if (projectType.value === 'nonfiction') {
      return 'Nonfiction usually reads Part -> Chapter -> Section. A part is the large argument block, a chapter develops one claim, a section is a smaller unit, and a note is planning-only.'
    }
    return 'Use Group for a large bucket, Chapter for a middle layer, Article for a real draft slot, and Note for planning-only reminders.'
  }
  if (projectType.value === 'novel') {
    return '小说通常是“分部 -> 章节 -> 场景”。分部是一卷、一幕或一大段；章节是读者看到的一章；场景是章节里的具体事件或一个正文位置；笔记只放规划提醒，不代表正文。'
  }
  if (projectType.value === 'essay') {
    return '散文集通常是“辑 -> 篇组 -> 篇章”。辑是一组主题，篇组收纳相近文章，篇章才是一篇真实作品；笔记只放规划提醒。'
  }
  if (projectType.value === 'nonfiction') {
    return '非虚构通常是“部分 -> 章节 -> 小节”。部分是一大块论述，章节推进一个主要问题，小节承载更小的论证或材料；笔记只放规划提醒。'
  }
  return '通用作品集可用“分组 -> 章节 -> 文章”。分组是大容器，章节是中层，文章才是正文位置；笔记只放规划提醒。'
})

interface CollectionTourStep {
  id: string
  title: string
  body: string
  target?: string
}

const collectionTourSteps = computed<CollectionTourStep[]>(() => {
  if (!store.selectedCollection) {
    return [
      {
        id: 'intro',
        title: t('collectionsTour.introTitle'),
        body: t('collectionsTour.introBody'),
        target: '[data-tour="collections-list"]',
      },
      {
        id: 'create',
        title: t('collectionsTour.createTitle'),
        body: t('collectionsTour.createBody'),
        target: '[data-tour="collections-create"]',
      },
    ]
  }
  return [
    {
      id: 'intro',
      title: t('collectionsTour.introTitle'),
      body: t('collectionsTour.introBody'),
      target: '[data-tour="collections-header"]',
    },
    {
      id: 'project-type',
      title: t('collectionsTour.projectTypeTitle'),
      body: t('collectionsTour.projectTypeBody'),
      target: '[data-tour="collections-project-type"]',
    },
    {
      id: 'add-articles',
      title: t('collectionsTour.addArticlesTitle'),
      body: t('collectionsTour.addArticlesBody'),
      target: '[data-tour="collections-add-articles"]',
    },
    {
      id: 'structure',
      title: t('collectionsTour.structureTitle'),
      body: t('collectionsTour.structureBody'),
      target: '[data-tour="collections-structure"]',
    },
    {
      id: 'create-node',
      title: t('collectionsTour.createNodeTitle'),
      body: t('collectionsTour.createNodeBody'),
      target: '[data-tour="outline-create-buttons"]',
    },
    {
      id: 'tree',
      title: t('collectionsTour.treeTitle'),
      body: t('collectionsTour.treeBody'),
      target: '[data-tour="manuscript-tree"]',
    },
    {
      id: 'child-node',
      title: t('collectionsTour.childNodeTitle'),
      body: t('collectionsTour.childNodeBody'),
      target: '[data-tour="outline-new-child"]',
    },
    {
      id: 'unplanned',
      title: t('collectionsTour.unplannedTitle'),
      body: t('collectionsTour.unplannedBody'),
      target: '[data-tour="unplanned-articles"]',
    },
    {
      id: 'node-types',
      title: t('collectionsTour.typeTitle'),
      body: t('collectionsTour.typeBody'),
      target: '[data-tour="outline-type-field"]',
    },
    {
      id: 'linked-article',
      title: t('collectionsTour.linkedArticleTitle'),
      body: t('collectionsTour.linkedArticleBody'),
      target: '[data-tour="outline-linked-article"]',
    },
    {
      id: 'fields',
      title: t('collectionsTour.fieldsTitle'),
      body: t('collectionsTour.fieldsBody'),
      target: '[data-tour="outline-detail-fields"]',
    },
    {
      id: 'board',
      title: t('collectionsTour.boardTitle'),
      body: t('collectionsTour.boardBody'),
      target: '[data-tour="collections-board"]',
    },
    {
      id: 'export',
      title: t('collectionsTour.exportTitle'),
      body: t('collectionsTour.exportBody'),
      target: '[data-tour="collections-export-panel"]',
    },
    {
      id: 'agent',
      title: t('collectionsTour.agentTitle'),
      body: t('collectionsTour.agentBody'),
      target: '[data-tour="collection-agent-panel"]',
    },
    {
      id: 'done',
      title: t('collectionsTour.doneTitle'),
      body: t('collectionsTour.doneBody'),
      target: '[data-tour="collections-tabs"]',
    },
  ]
})

const currentTourProgressLabel = computed(() =>
  t('collectionsTour.progress', {
    current: Math.min(tourStepIndex.value + 1, collectionTourSteps.value.length),
    total: collectionTourSteps.value.length,
  })
)

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  await store.loadCollections()
  const routeCollectionId = typeof route.query.id === 'string' ? route.query.id : ''
  const lastCollectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (routeCollectionId && store.collections.some((collection) => collection.id === routeCollectionId)) {
    await store.selectCollection(routeCollectionId)
  } else if (lastCollectionId && store.collections.some((collection) => collection.id === lastCollectionId)) {
    await store.selectCollection(lastCollectionId)
  }
  allArticles.value = await articlesApi.listArticles(500)
  await applyCollectionRouteContext()
  if (route.query.tour === 'collection' || !settings.collectionsTourDismissed) {
    startCollectionTour()
    if (route.query.tour === 'collection') {
      void clearCollectionTourQuery()
    }
  }
})

watch(
  () => store.selectedCollectionId,
  (id, previousId) => {
    if (id) localStorage.setItem(LAST_SELECTED_COLLECTION_KEY, id)
    if (id === previousId || previousId === undefined) return
    stopAgentPolling()
    agentLoadToken += 1
    agentReferenceSearchToken += 1
    agentState.value = null
    agentError.value = null
    agentApplyingActionId.value = null
    agentRunning.value = false
    actionError.value = null
    outlineActionError.value = null
    selectedAgentRefs.value = []
    agentReferenceResults.value = []
    agentReferencePickerOpen.value = false
    selectedAgentDraftId.value = null
  },
  { immediate: true }
)

watch(
  () => store.selectedCollection,
  (collection) => {
    draftTitle.value = collection?.title ?? ''
    draftDescription.value = collection?.description ?? ''
    draftProjectType.value = collectionProjectType(collection)
    collectionMetaEditing.value = false
    collectionActionsOpen.value = false
  },
  { immediate: true }
)

watch(
  () => store.selectedOutlineItem,
  (item) => {
    loadOutlineDraft(item)
    outlineEditing.value = false
    outlineAdvancedOpen.value = false
    outlineCreateMenuOpen.value = false
  },
  { immediate: true }
)

watch(
  () => route.query.tour,
  (value) => {
    if (value === 'collection') {
      startCollectionTour()
      void clearCollectionTourQuery()
    }
  }
)

watch(
  () => [route.query.id, route.query.article, route.query.tab] as const,
  () => {
    void applyCollectionRouteContext()
  }
)

watch(
  () => store.selectedCollectionId,
  () => {
    if (!tourOpen.value) return
    tourStepIndex.value = 0
    prepareCollectionTourStep(0)
  }
)

watch(
  () => [viewMode.value, store.selectedCollectionId] as const,
  ([mode, collectionId]) => {
    if (mode === 'agent' && collectionId) {
      void loadAgentState()
    }
  }
)

onBeforeUnmount(() => {
  stopAgentPolling()
  window.removeEventListener('resize', handleWindowResize)
  clearCollectionArticleHighlightTimer()
})

function handleWindowResize() {
  const previousWidth = windowWidth.value
  windowWidth.value = window.innerWidth
  if (previousWidth >= 1280 && windowWidth.value < 1280) {
    agentLeftPanelOpen.value = false
  }
  if (previousWidth >= 1760 && windowWidth.value < 1760) {
    agentRightPanelOpen.value = false
  }
}

function prepareCollectionTourStep(index = tourStepIndex.value) {
  const step = collectionTourSteps.value[index]
  if (!step || !store.selectedCollection) return
  outlineEditing.value = ['node-types', 'linked-article', 'fields'].includes(step.id)
  if (step.id === 'board') {
    viewMode.value = 'board'
  } else if (step.id === 'export') {
    viewMode.value = 'export'
  } else if (step.id === 'agent') {
    viewMode.value = 'agent'
  } else {
    viewMode.value = 'structure'
  }
}

function startCollectionTour() {
  tourStepIndex.value = 0
  tourOpen.value = true
  prepareCollectionTourStep(0)
}

function closeCollectionTour() {
  tourOpen.value = false
  outlineEditing.value = false
  settings.dismissCollectionsTour()
  void clearCollectionTourQuery()
}

function finishCollectionTour() {
  closeCollectionTour()
}

async function clearCollectionTourQuery() {
  if (route.query.tour !== 'collection') return
  const query = { ...route.query }
  delete query.tour
  await router.replace({ name: 'collections', query })
}

async function applyCollectionRouteContext() {
  const collectionId = typeof route.query.id === 'string' ? route.query.id : ''
  if (collectionId && store.collections.some((collection) => collection.id === collectionId)) {
    if (store.selectedCollectionId !== collectionId) {
      await store.selectCollection(collectionId)
    }
  } else if (collectionId && store.collections.length) {
    actionError.value = '要打开的作品集已不存在。'
    return
  }

  const tab = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (tab === 'agent') viewMode.value = 'agent'
  else if (tab === 'board') viewMode.value = 'board'
  else if (tab === 'export') viewMode.value = 'export'

  const articleId = typeof route.query.article === 'string' ? route.query.article : ''
  if (!articleId || !store.selectedCollectionId) return
  setCollectionArticleHighlight(articleId)
  if (!tab) viewMode.value = 'structure'
  const linkedItem = store.outline.find((item) => item.entry_id === articleId)
  const inCollection = store.articles.some((article) => article.id === articleId)
  if (!inCollection) {
    actionError.value = '这篇文章已不在当前作品集中。'
    return
  }
  if (linkedItem) {
    store.selectOutlineItem(linkedItem.id)
  }
  await nextTick()
  scrollToCollectionArticle(articleId)
}

function clearCollectionArticleHighlightTimer() {
  if (collectionArticleHighlightTimer !== null) {
    window.clearTimeout(collectionArticleHighlightTimer)
    collectionArticleHighlightTimer = null
  }
}

function setCollectionArticleHighlight(articleId: string | null) {
  clearCollectionArticleHighlightTimer()
  highlightedCollectionArticleId.value = articleId
  if (articleId) {
    collectionArticleHighlightTimer = window.setTimeout(() => {
      if (highlightedCollectionArticleId.value === articleId) highlightedCollectionArticleId.value = null
      collectionArticleHighlightTimer = null
    }, ROUTE_HIGHLIGHT_MS)
  }
}

function scrollToCollectionArticle(articleId: string) {
  const target = Array
    .from(document.querySelectorAll<HTMLElement>('[data-collection-article-id]'))
    .find((element) => element.dataset.collectionArticleId === articleId)
  if (target instanceof HTMLElement) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function scrollToOutlineItem(itemId: string) {
  const target = document.querySelector<HTMLElement>(`[data-outline-item-id="${itemId}"]`)
  if (target instanceof HTMLElement) {
    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
}

async function nextCollectionTourStep() {
  tourStepIndex.value = Math.min(tourStepIndex.value + 1, collectionTourSteps.value.length - 1)
  prepareCollectionTourStep()
  await nextTick()
}

async function previousCollectionTourStep() {
  tourStepIndex.value = Math.max(tourStepIndex.value - 1, 0)
  prepareCollectionTourStep()
  await nextTick()
}

function stopAgentPolling() {
  if (agentPollTimer !== null) {
    window.clearTimeout(agentPollTimer)
    agentPollTimer = null
  }
}

function isTerminalAgentRun(run: CollectionAgentRun | null): boolean {
  return Boolean(run && ['succeeded', 'failed', 'cancelled'].includes(run.status))
}

function syncAgentDrafts(state: CollectionAgentState) {
  agentDefaultProfileId.value = state.settings.profile_id || 'default'
  agentProfileId.value = agentDefaultProfileId.value
  const activeSession = (state.sessions ?? []).find((session) => session.id === state.active_session_id)
  agentMode.value = activeSession?.mode ?? 'discuss'
  const next: Record<string, string> = {}
  for (const section of state.memory.sections) {
    next[section.id] = section.content || ''
  }
  agentMemoryDraft.value = next
  agentStyleSamples.value = state.style_samples ?? []
  agentPortraitTagsText.value = (state.author_portrait?.tags ?? []).join(', ')
  agentPortraitSummary.value = state.author_portrait?.summary ?? ''
  const drafts = state.drafts ?? []
  if (selectedAgentDraftId.value && !drafts.some((draft) => draft.id === selectedAgentDraftId.value)) {
    selectedAgentDraftId.value = null
  }
  if (!selectedAgentDraftId.value && drafts.length) {
    selectedAgentDraftId.value = drafts.find((draft) => draft.status === 'draft')?.id ?? drafts[0].id
  }
  syncSelectedAgentDraftEditor()
}

function syncAgentRunCollapse(state: CollectionAgentState) {
  const validIds = new Set(state.runs.map((run) => run.id))
  const collapsed = new Set(agentCollapsedRunIds.value.filter((id) => validIds.has(id)))
  for (const run of state.runs) {
    if (
      agentRunAnswer(run).length > AGENT_LONG_ANSWER_THRESHOLD
      && !agentExpandedRunIds.value.includes(run.id)
    ) {
      collapsed.add(run.id)
    }
  }
  agentCollapsedRunIds.value = [...collapsed]
  agentExpandedRunIds.value = agentExpandedRunIds.value.filter((id) => validIds.has(id))
}

async function loadAgentState(sessionId?: string | null) {
  if (!store.selectedCollectionId) return
  const token = ++agentLoadToken
  const collectionId = store.selectedCollectionId
  agentLoading.value = true
  agentError.value = null
  try {
    const state = await collectionsApi.getAgentState(collectionId, sessionId)
    if (token !== agentLoadToken || store.selectedCollectionId !== collectionId) return
    agentState.value = state
    syncAgentDrafts(state)
    syncAgentRunCollapse(state)
    const running = activeAgentRun.value
    if (running && !isTerminalAgentRun(running)) scheduleAgentPoll(running.id)
  } catch (e) {
    if (token !== agentLoadToken || store.selectedCollectionId !== collectionId) return
    agentError.value = errorMessage(e)
  } finally {
    if (token === agentLoadToken && store.selectedCollectionId === collectionId) {
      agentLoading.value = false
    }
  }
}

function syncSelectedAgentDraftEditor() {
  const draft = selectedAgentDraft.value
  agentDraftTitle.value = draft?.title ?? ''
  agentDraftContent.value = draft?.content ?? ''
}

function selectAgentDraft(draft: CollectionAgentDraft) {
  selectedAgentDraftId.value = draft.id
  openAgentRightPanel('drafts')
  syncSelectedAgentDraftEditor()
}

function selectAgentDraftById(draftId: string | null) {
  if (!draftId) return
  const draft = (agentState.value?.drafts ?? []).find((item) => item.id === draftId)
  if (draft) selectAgentDraft(draft)
}

function setAgentRightTab(tab: 'context' | 'drafts' | 'memory') {
  agentRightTab.value = tab
}

function toggleAgentLeftPanel() {
  const next = !agentLeftPanelOpen.value
  agentLeftPanelOpen.value = next
  if (next && windowWidth.value < 1280) agentRightPanelOpen.value = false
}

function toggleAgentRightPanel() {
  const next = !agentRightPanelOpen.value
  agentRightPanelOpen.value = next
  if (next && windowWidth.value < 1280) agentLeftPanelOpen.value = false
}

function openAgentRightPanel(tab: 'context' | 'drafts' | 'memory' = agentRightTab.value) {
  agentRightTab.value = tab
  agentRightPanelOpen.value = true
  if (windowWidth.value < 1280) agentLeftPanelOpen.value = false
}

function setAgentDraftApplyOperation(operation: 'create_article' | 'append' | 'replace_selection') {
  agentDraftApplyOperation.value = operation
}

function toggleAgentDraftSelection(draftId: string) {
  agentDraftSelectedIds.value = agentDraftSelectedIds.value.includes(draftId)
    ? agentDraftSelectedIds.value.filter((id) => id !== draftId)
    : [...agentDraftSelectedIds.value, draftId]
}

async function createAgentSession() {
  if (!store.selectedCollectionId) return
  agentSessionBusy.value = true
  agentError.value = null
  try {
    const session = await collectionsApi.createAgentSession(store.selectedCollectionId, {
      title: agentNewSessionTitle.value.trim() || (locale.value === 'en' ? 'New conversation' : '新会话'),
      mode: agentMode.value,
    })
    agentNewSessionTitle.value = ''
    agentCreatingSession.value = false
    await loadAgentState(session.id)
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentSessionBusy.value = false
  }
}

async function switchAgentSession(session: CollectionAgentSession) {
  if (!store.selectedCollectionId || session.id === agentState.value?.active_session_id) return
  stopAgentPolling()
  selectedAgentRefs.value = []
  agentPrompt.value = ''
  selectedAgentDraftId.value = null
  if (session.archived) {
    try {
      await collectionsApi.updateAgentSession(store.selectedCollectionId, session.id, { archived: false })
    } catch (e) {
      agentError.value = errorMessage(e)
      return
    }
  }
  await loadAgentState(session.id)
}

async function switchAgentSessionById(event: Event) {
  const sessionId = (event.target as HTMLSelectElement).value
  const session = (agentState.value?.sessions ?? []).find((item) => item.id === sessionId)
  if (session) await switchAgentSession(session)
}

async function archiveActiveAgentSession() {
  if (!store.selectedCollectionId || !activeAgentSession.value || activeAgentRun.value) return
  agentSessionBusy.value = true
  try {
    await collectionsApi.updateAgentSession(store.selectedCollectionId, activeAgentSession.value.id, { archived: true })
    const nextSession = (agentState.value?.sessions ?? []).find((item) => !item.archived && item.id !== activeAgentSession.value?.id)
    if (nextSession) await loadAgentState(nextSession.id)
    else {
      agentNewSessionTitle.value = locale.value === 'en' ? 'New conversation' : '新会话'
      await createAgentSession()
    }
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentSessionBusy.value = false
  }
}

function startRenamingAgentSession() {
  if (!activeAgentSession.value) return
  agentSessionTitleDraft.value = activeAgentSession.value.title
  agentRenamingSession.value = true
}

async function saveAgentSessionTitle() {
  if (!store.selectedCollectionId || !activeAgentSession.value) return
  const title = agentSessionTitleDraft.value.trim()
  if (!title) return
  try {
    const updated = await collectionsApi.updateAgentSession(
      store.selectedCollectionId,
      activeAgentSession.value.id,
      { title },
    )
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        sessions: agentState.value.sessions.map((item) => item.id === updated.id ? updated : item),
      }
    }
    agentRenamingSession.value = false
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function deleteActiveAgentSession() {
  if (!store.selectedCollectionId || !activeAgentSession.value || activeAgentRun.value) return
  if (!window.confirm(agentCopy.value.deleteSessionConfirm)) return
  agentSessionBusy.value = true
  try {
    await collectionsApi.deleteAgentSession(store.selectedCollectionId, activeAgentSession.value.id)
    selectedAgentDraftId.value = null
    await loadAgentState()
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentSessionBusy.value = false
  }
}

async function changeAgentMode(mode: CollectionAgentMode) {
  agentMode.value = mode
  if (!store.selectedCollectionId || !activeAgentSession.value) return
  try {
    const updated = await collectionsApi.updateAgentSession(
      store.selectedCollectionId,
      activeAgentSession.value.id,
      { mode },
    )
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        sessions: agentState.value.sessions.map((item) => item.id === updated.id ? updated : item),
      }
    }
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function compactActiveAgentSession() {
  if (!store.selectedCollectionId || !activeAgentSession.value) return
  try {
    const updated = await collectionsApi.compactAgentSession(store.selectedCollectionId, activeAgentSession.value.id)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        sessions: agentState.value.sessions.map((item) => item.id === updated.id ? updated : item),
      }
    }
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

function splitAgentBriefList(value: string): string[] {
  return value.split(/[\n,，]/).map((item) => item.trim()).filter(Boolean)
}

async function saveSelectedAgentDraft() {
  if (!store.selectedCollectionId || !selectedAgentDraft.value) return
  agentDraftSaving.value = true
  agentError.value = null
  try {
    const updated = await collectionsApi.updateAgentDraft(
      store.selectedCollectionId,
      selectedAgentDraft.value.id,
      {
        title: agentDraftTitle.value,
        content: agentDraftContent.value,
        brief: selectedAgentDraft.value.brief,
      },
    )
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        drafts: agentState.value.drafts.map((item) => item.id === updated.id ? updated : item),
      }
    }
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentDraftSaving.value = false
  }
}

function openAgentDraftApply(draft: CollectionAgentDraft) {
  selectAgentDraft(draft)
  agentDraftApplyOperation.value = 'create_article'
  agentDraftArticleTitle.value = draft.title
  agentDraftTargetEntryId.value = store.articles[0]?.id ?? ''
  agentDraftSelectionText.value = ''
  agentDraftApplyOpen.value = true
}

async function sha256Text(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function applySelectedAgentDraft() {
  if (!store.selectedCollectionId || !selectedAgentDraft.value) return
  const draft = selectedAgentDraft.value
  agentDraftApplying.value = true
  agentError.value = null
  try {
    const payload: Parameters<typeof collectionsApi.applyAgentDraft>[2] = {
      operation: agentDraftApplyOperation.value,
      article_title: agentDraftArticleTitle.value,
    }
    if (agentDraftApplyOperation.value !== 'create_article') {
      const article = allArticles.value.find((item) => item.id === agentDraftTargetEntryId.value)
        ?? store.articles.find((item) => item.id === agentDraftTargetEntryId.value)
      if (!article) throw new Error('请选择目标文章。')
      payload.target_entry_id = article.id
      payload.expected_body_hash = await sha256Text(article.body)
      if (agentDraftApplyOperation.value === 'replace_selection') {
        const selectedText = agentDraftSelectionText.value
        if (!selectedText.trim()) throw new Error('请粘贴要替换的明确原文。')
        const start = article.body.indexOf(selectedText)
        if (start < 0 || article.body.indexOf(selectedText, start + 1) >= 0) {
          throw new Error('这段原文不存在或出现多次，请选择更完整、唯一的一段。')
        }
        payload.selection_start = start
        payload.selection_end = start + selectedText.length
        payload.expected_selected_text = selectedText
      }
    }
    const result = await collectionsApi.applyAgentDraft(store.selectedCollectionId, draft.id, payload)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        drafts: agentState.value.drafts.map((item) => item.id === result.draft.id ? result.draft : item),
      }
    }
    agentDraftApplyOpen.value = false
    await Promise.all([
      store.loadArticles(store.selectedCollectionId),
      articlesApi.listArticles(500).then((items) => { allArticles.value = items }),
    ])
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentDraftApplying.value = false
  }
}

async function deleteSelectedAgentDrafts(clearAll = false) {
  if (!store.selectedCollectionId) return
  const ids = clearAll
    ? []
    : (agentDraftSelectedIds.value.length ? agentDraftSelectedIds.value : selectedAgentDraftId.value ? [selectedAgentDraftId.value] : [])
  if (!clearAll && !ids.length) return
  try {
    await collectionsApi.deleteAgentDrafts(store.selectedCollectionId, ids, clearAll)
    agentDraftSelectedIds.value = []
    selectedAgentDraftId.value = null
    await loadAgentState(agentState.value?.active_session_id)
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function requestAgentDraftVariant(draft: CollectionAgentDraft) {
  selectAgentDraft(draft)
  await runAgentPrompt(
    'draft_variant',
    `请保留场景目标和 canon，写一个明显不同但同样可用的版本。原草稿标题：${draft.title}`,
    'draft',
    draft.id,
  )
}

async function startAgentStyleCycle() {
  if (!store.selectedCollectionId || !agentStyleEntryId.value) return
  try {
    const sample = await collectionsApi.startAgentStyleSample(store.selectedCollectionId, agentStyleEntryId.value)
    agentStyleSamples.value = [sample, ...agentStyleSamples.value.filter((item) => item.id !== sample.id)]
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function completeAgentStyleCycle() {
  if (!store.selectedCollectionId || !activeStyleSample.value) return
  try {
    const sample = await collectionsApi.completeAgentStyleSample(store.selectedCollectionId, activeStyleSample.value.id)
    agentStyleSamples.value = agentStyleSamples.value.map((item) => item.id === sample.id ? sample : item)
    await loadAgentState(agentState.value?.active_session_id)
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function saveAgentPortrait() {
  if (!store.selectedCollectionId) return
  agentPortraitSaving.value = true
  try {
    const portrait = await collectionsApi.saveAuthorPortrait(store.selectedCollectionId, {
      tags: splitAgentBriefList(agentPortraitTagsText.value),
      summary: agentPortraitSummary.value,
    })
    if (agentState.value) agentState.value = { ...agentState.value, author_portrait: portrait }
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentPortraitSaving.value = false
  }
}

async function loadAgentPortraitHistory() {
  if (!store.selectedCollectionId) return
  try {
    agentPortraitVersions.value = await collectionsApi.listAuthorPortraitVersions(store.selectedCollectionId)
    agentPortraitHistoryOpen.value = true
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function restoreAgentPortraitVersion(versionId: string) {
  if (!store.selectedCollectionId) return
  try {
    const portrait = await collectionsApi.restoreAuthorPortraitVersion(store.selectedCollectionId, versionId)
    if (agentState.value) agentState.value = { ...agentState.value, author_portrait: portrait }
    agentPortraitTagsText.value = portrait.tags.join(', ')
    agentPortraitSummary.value = portrait.summary
    agentPortraitHistoryOpen.value = false
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function requestAuthorPortraitProposal() {
  agentRightTab.value = 'memory'
  await runAgentPrompt(
    'author_portrait',
    '请根据已经完成的作者原稿与最终确认稿闭环样本，整理一份作者画像更新提案。只提取反复稳定的写作倾向，不要把外部引用或被拒绝的 Agent 草稿算作作者风格。',
    'review',
  )
}

function scheduleAgentPoll(runId: string) {
  stopAgentPolling()
  agentPollTimer = window.setTimeout(() => {
    void pollAgentRun(runId)
  }, 1500)
}

async function pollAgentRun(runId: string) {
  if (!store.selectedCollectionId) return
  const collectionId = store.selectedCollectionId
  try {
    const run = await collectionsApi.getAgentRun(collectionId, runId)
    if (store.selectedCollectionId !== collectionId) return
    if (agentState.value) {
      const runs = [...agentState.value.runs]
      const index = runs.findIndex((item) => item.id === run.id)
      if (index === -1) runs.unshift(run)
      else runs[index] = run
      agentState.value = {
        ...agentState.value,
        runs,
        active_run: isTerminalAgentRun(run) ? null : run,
      }
      syncAgentRunCollapse(agentState.value)
    }
    if (isTerminalAgentRun(run)) {
      const currentSessionId = agentState.value?.active_session_id
      if (run.draft_id && run.session_id === currentSessionId) {
        selectedAgentDraftId.value = run.draft_id
        openAgentRightPanel('drafts')
      }
      await loadAgentState(currentSessionId)
    } else {
      scheduleAgentPoll(run.id)
    }
  } catch (e) {
    if (store.selectedCollectionId !== collectionId) return
    agentError.value = `正在重连 Agent 状态：${errorMessage(e)}`
    scheduleAgentPoll(runId)
  }
}

async function saveAgentSettings() {
  if (!store.selectedCollectionId || !agentState.value) return
  agentError.value = null
  try {
    const settings = await collectionsApi.saveAgentSettings(store.selectedCollectionId, {
      profile_id: agentDefaultProfileId.value || 'default',
      enabled: agentState.value.settings.enabled,
    })
    agentState.value = { ...agentState.value, settings }
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

async function saveAgentMemory() {
  if (!store.selectedCollectionId || !agentState.value) return
  agentMemorySaving.value = true
  agentError.value = null
  try {
    const memory: CollectionAgentMemory = await collectionsApi.saveAgentMemory(
      store.selectedCollectionId,
      agentMemoryDraft.value,
    )
    agentState.value = { ...agentState.value, memory }
    syncAgentDrafts(agentState.value)
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentMemorySaving.value = false
  }
}

async function searchAgentReferences() {
  if (!store.selectedCollectionId) return
  const token = ++agentReferenceSearchToken
  const collectionId = store.selectedCollectionId
  agentReferencePickerOpen.value = true
  agentSearchLoading.value = true
  agentError.value = null
  try {
    const results = await collectionsApi.searchAgentReferences(
      collectionId,
      agentReferenceQuery.value.trim(),
      30,
    )
    if (token !== agentReferenceSearchToken || store.selectedCollectionId !== collectionId) return
    agentReferenceResults.value = results
  } catch (e) {
    if (token !== agentReferenceSearchToken || store.selectedCollectionId !== collectionId) return
    agentError.value = errorMessage(e)
  } finally {
    if (token === agentReferenceSearchToken && store.selectedCollectionId === collectionId) {
      agentSearchLoading.value = false
    }
  }
}

function openAgentReferencePicker(query = agentReferenceQuery.value) {
  agentReferenceQuery.value = query
  agentReferencePickerOpen.value = true
  void searchAgentReferences()
}

function closeAgentReferencePicker() {
  agentReferencePickerOpen.value = false
}

function clearAgentReferenceSearch() {
  agentReferenceQuery.value = ''
  agentReferenceResults.value = []
}

function addAgentReference(ref: CollectionAgentReference) {
  const mention = agentPrompt.value.match(/(^|\s)@[^\s@]{0,40}$/)
  if (mention && typeof mention.index === 'number') {
    agentPrompt.value = `${agentPrompt.value.slice(0, mention.index)}${mention[1] ?? ''}`
  }
  if (!selectedAgentRefs.value.some((item) => item.kind === ref.kind && item.ref_id === ref.ref_id)) {
    selectedAgentRefs.value = [...selectedAgentRefs.value, ref]
  }
  agentReferencePickerOpen.value = false
}

function removeAgentReference(ref: CollectionAgentReference) {
  selectedAgentRefs.value = selectedAgentRefs.value.filter((item) =>
    !(item.kind === ref.kind && item.ref_id === ref.ref_id)
  )
}

function closeAgentSlashMenu() {
  agentSlashMenuOpen.value = false
  agentSlashQuery.value = ''
  agentSlashSelectedIndex.value = 0
}

function syncAgentSlashMenuFromPrompt() {
  const match = agentPrompt.value.match(/^\/([A-Za-z0-9_-]*)$/)
  if (!match) {
    if (agentSlashMenuOpen.value) closeAgentSlashMenu()
    return
  }
  agentSlashQuery.value = match[1] || ''
  agentSlashMenuOpen.value = true
  agentReferencePickerOpen.value = false
  if (agentSlashSelectedIndex.value >= filteredAgentSlashCommands.value.length) {
    agentSlashSelectedIndex.value = Math.max(0, filteredAgentSlashCommands.value.length - 1)
  }
}

function moveAgentSlashSelection(direction: 1 | -1) {
  const total = filteredAgentSlashCommands.value.length
  if (!total) return
  agentSlashSelectedIndex.value = (agentSlashSelectedIndex.value + direction + total) % total
}

function selectAgentSlashCommand(command = filteredAgentSlashCommands.value[agentSlashSelectedIndex.value]) {
  if (!command) return
  closeAgentSlashMenu()
  agentPrompt.value = ''
  if (command.action === 'clear') {
    requestAgentClear()
    return
  }
  if (command.taskKind) {
    runQuickAgentTask(command.taskKind)
  }
}

function runAgentSlashCommandText(message: string): boolean {
  if (!message.startsWith('/')) return false
  const commandName = message.slice(1).trim().toLowerCase()
  const command = agentSlashCommands.value.find((item) => item.command === commandName)
  if (command) {
    selectAgentSlashCommand(command)
    return true
  }
  agentError.value = '未知斜杠命令。输入 / 后从菜单选择可用功能。'
  agentSlashQuery.value = commandName
  agentSlashSelectedIndex.value = 0
  agentSlashMenuOpen.value = true
  return true
}

function handleAgentPromptKeydown(event: KeyboardEvent) {
  if (agentSlashMenuOpen.value) {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeAgentSlashMenu()
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      moveAgentSlashSelection(1)
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      moveAgentSlashSelection(-1)
      return
    }
    if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault()
      selectAgentSlashCommand()
      return
    }
  }
  if (event.key === 'Escape' && agentReferencePickerOpen.value) {
    agentReferencePickerOpen.value = false
    return
  }
  if (event.key === '@') {
    agentReferencePickerOpen.value = true
    agentReferenceQuery.value = ''
    void searchAgentReferences()
  }
}

function handleAgentPromptInput() {
  syncAgentSlashMenuFromPrompt()
  if (agentSlashMenuOpen.value) return
  const match = agentPrompt.value.match(/(?:^|\s)@([^\s@]{0,40})$/)
  if (!match) return
  agentReferenceQuery.value = match[1] || ''
  agentReferencePickerOpen.value = true
  void searchAgentReferences()
}

async function runAgentPrompt(
  taskType = 'free_chat',
  prompt = agentPrompt.value,
  forcedMode?: CollectionAgentMode,
  parentDraftId?: string,
) {
  if (!store.selectedCollectionId) return
  const message = prompt.trim()
  if (runAgentSlashCommandText(message)) {
    return
  }
  if (!message) {
    agentError.value = '请先输入要交给作品集 Agent 的问题或任务。'
    return
  }
  if (activeAgentRun.value) {
    agentError.value = 'Agent 正在工作，请等待完成或先中断本地等待。'
    return
  }
  agentRunning.value = true
  agentError.value = null
  const runMode = forcedMode ?? agentMode.value
  try {
    const run = await collectionsApi.createAgentRun(store.selectedCollectionId, {
      message,
      task_type: taskType,
      request_web_context: agentRequestWebContext.value,
      profile_id: agentProfileId.value,
      session_id: agentState.value?.active_session_id,
      mode: runMode,
      draft_brief: runMode === 'draft'
        ? {
            ...agentDraftBrief.value,
            target_length: Number(agentDraftBrief.value.target_length) >= 100
              ? Number(agentDraftBrief.value.target_length)
              : null,
            must_happen: splitAgentBriefList(agentDraftMustHappenText.value),
            avoid: splitAgentBriefList(agentDraftAvoidText.value),
          }
        : null,
      parent_draft_id: parentDraftId ?? null,
      context_refs: selectedAgentRefs.value.map((ref) => ({ kind: ref.kind, ref_id: ref.ref_id })),
    })
    if (agentState.value) {
      agentState.value = { ...agentState.value, runs: [run, ...agentState.value.runs], active_run: run }
    }
    agentPrompt.value = ''
    closeAgentSlashMenu()
    agentPendingQuickTask.value = null
    if (runMode === 'draft') {
      openAgentRightPanel('drafts')
    }
    scheduleAgentPoll(run.id)
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentRunning.value = false
  }
}

function runQuickAgentTask(kind: AgentQuickTaskKind) {
  agentPendingQuickTask.value = kind
}

async function confirmQuickAgentTask() {
  if (!pendingQuickTask.value) return
  const modeByTask: Record<AgentQuickTaskKind, CollectionAgentMode> = {
    init: 'discuss',
    health: 'review',
    continuity: 'review',
    next: 'plan',
    memory: 'plan',
  }
  await runAgentPrompt(
    pendingQuickTask.value.kind,
    pendingQuickTask.value.prompt,
    modeByTask[pendingQuickTask.value.kind],
  )
}

function cancelQuickAgentTask() {
  agentPendingQuickTask.value = null
}

async function cancelActiveAgentRun() {
  if (!store.selectedCollectionId || !activeAgentRun.value) return
  try {
    const run = await collectionsApi.cancelAgentRun(store.selectedCollectionId, activeAgentRun.value.id)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        active_run: null,
        runs: agentState.value.runs.map((item) => item.id === run.id ? run : item),
      }
    }
    stopAgentPolling()
  } catch (e) {
    agentError.value = errorMessage(e)
  }
}

function requestAgentClear() {
  if (activeAgentRun.value) {
    agentError.value = 'Agent 正在工作，请等待完成或先中断本地等待。'
    return
  }
  agentClearDialogOpen.value = true
}

async function clearAgentConversation() {
  if (!store.selectedCollectionId || activeAgentRun.value) return
  agentClearing.value = true
  agentError.value = null
  try {
    const state = await collectionsApi.clearAgentConversation(store.selectedCollectionId)
    agentState.value = state
    agentPrompt.value = ''
    agentReferenceResults.value = []
    selectedAgentRefs.value = []
    agentPendingQuickTask.value = null
    agentCollapsedRunIds.value = []
    agentExpandedRunIds.value = []
    syncAgentDrafts(state)
    syncAgentRunCollapse(state)
    agentClearDialogOpen.value = false
  } catch (e) {
    agentError.value = errorMessage(e)
  } finally {
    agentClearing.value = false
  }
}

async function applyAgentAction(action: CollectionAgentAction) {
  if (!store.selectedCollectionId) return
  const collectionId = store.selectedCollectionId
  agentApplyingActionId.value = action.id
  agentError.value = null
  try {
    const updated = await collectionsApi.applyAgentAction(collectionId, action.id)
    if (store.selectedCollectionId !== collectionId) return
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        actions: agentState.value.actions.map((item) => item.id === updated.id ? updated : item),
        runs: agentState.value.runs.map((run) => ({
          ...run,
          actions: run.actions.map((item) => item.id === updated.id ? updated : item),
        })),
      }
    }
    await Promise.all([
      store.loadOutline(),
      store.loadArticles(),
      loadAgentState(),
    ])
  } catch (e) {
    if (store.selectedCollectionId !== collectionId) return
    agentError.value = errorMessage(e)
  } finally {
    if (store.selectedCollectionId === collectionId) agentApplyingActionId.value = null
  }
}

async function rejectAgentAction(action: CollectionAgentAction) {
  if (!store.selectedCollectionId) return
  const collectionId = store.selectedCollectionId
  agentApplyingActionId.value = action.id
  agentError.value = null
  try {
    const updated = await collectionsApi.rejectAgentAction(collectionId, action.id)
    if (store.selectedCollectionId !== collectionId) return
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        actions: agentState.value.actions.map((item) => item.id === updated.id ? updated : item),
        runs: agentState.value.runs.map((run) => ({
          ...run,
          actions: run.actions.map((item) => item.id === updated.id ? updated : item),
        })),
      }
    }
  } catch (e) {
    if (store.selectedCollectionId !== collectionId) return
    agentError.value = errorMessage(e)
  } finally {
    if (store.selectedCollectionId === collectionId) agentApplyingActionId.value = null
  }
}

async function deferAgentAction(action: CollectionAgentAction) {
  if (!store.selectedCollectionId) return
  const collectionId = store.selectedCollectionId
  agentApplyingActionId.value = action.id
  agentError.value = null
  try {
    const updated = await collectionsApi.deferAgentAction(collectionId, action.id)
    if (store.selectedCollectionId !== collectionId) return
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        actions: agentState.value.actions.map((item) => item.id === updated.id ? updated : item),
        runs: agentState.value.runs.map((run) => ({
          ...run,
          actions: run.actions.map((item) => item.id === updated.id ? updated : item),
        })),
      }
    }
  } catch (e) {
    if (store.selectedCollectionId !== collectionId) return
    agentError.value = errorMessage(e)
  } finally {
    if (store.selectedCollectionId === collectionId) agentApplyingActionId.value = null
  }
}

function agentReferenceKindLabel(kind: string): string {
  const labels = locale.value === 'en'
    ? { outline: 'Outline', article: 'Article', ai_card: 'AI Card', motif: 'Motif', reference: 'Reference' }
    : { outline: '结构', article: '文章', ai_card: 'AI卡片', motif: '意象', reference: '文脉' }
  if (kind in labels) return labels[kind as keyof typeof labels]
  return kind
}

function agentActionTypeLabel(type: string): string {
  const labels = locale.value === 'en'
    ? {
        update_memory: 'Update memory',
        create_outline_item: 'Create outline item',
        update_outline_item: 'Update outline item',
        create_article_note: 'Create article note',
        update_author_portrait: 'Update Author Portrait',
      }
    : {
        update_memory: '更新记忆',
        create_outline_item: '新增结构',
        update_outline_item: '修改结构',
        create_article_note: '创建便签',
        update_author_portrait: '更新作者画像',
      }
  if (type in labels) return labels[type as keyof typeof labels]
  return type
}

function agentStageLabel(run: CollectionAgentRun): string {
  if (locale.value !== 'en') return run.stage_label
  const labels: Record<string, string> = {
    queued: 'Queued',
    preparing_context: 'Preparing collection context',
    sending_request: 'Sending request',
    waiting_model: 'Request sent, waiting for model',
    parsing_response: 'Parsing Agent response',
    building_proposals: 'Building reviewable proposals',
    succeeded: 'Complete',
    failed: 'Failed',
    cancelled: 'Interrupted',
  }
  return labels[run.stage] || run.stage_label
}

function agentMemorySectionCopy(section: { id: string; title: string; help: string }): { title: string; help: string } {
  if (locale.value !== 'en') return { title: section.title, help: section.help }
  const sections: Record<string, { title: string; help: string }> = {
    project_core: { title: 'Project Core', help: 'Genre, central question, primary conflict, and narrative promise.' },
    characters: { title: 'Characters & Relationships', help: 'Major characters, desires, contradictions, and changing relationships.' },
    timeline: { title: 'Timeline', help: 'Key event order, breaks, and dates that are still uncertain.' },
    world: { title: 'Places & World', help: 'Spaces, institutions, rules, and important environments.' },
    style: { title: 'Themes & Style', help: 'Narrative voice, aesthetic constraints, and directions to avoid.' },
    foreshadowing: { title: 'Setup & Payoff', help: 'Planted clues, unresolved setups, and continuity risks.' },
    decisions: { title: 'Decision Log', help: 'Author-confirmed canon facts and structural decisions.' },
    open_questions: { title: 'Open Questions', help: 'Unsettled setting, character, and structure questions.' },
  }
  return sections[section.id] || { title: section.title, help: section.help }
}

function agentActionStatusTone(status: string): string {
  if (status === 'applied') return 'bg-emerald-50 text-emerald-700 ring-emerald-100'
  if (status === 'rejected') return 'bg-stone-100 text-stone-500 ring-stone-200'
  return 'bg-amber-50 text-amber-700 ring-amber-100'
}

function agentActionStatusLabel(status: string): string {
  if (status === 'applied') return agentCopy.value.appliedStatus
  if (status === 'rejected') return agentCopy.value.rejectedStatus
  if (status === 'deferred') return agentCopy.value.deferredStatus
  return status
}

function agentModeLabel(mode: string): string {
  return agentModeOptions.value.find((item) => item.value === mode)?.label || mode
}

function formatAgentPreview(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2)
}

function agentRunAnswer(run: CollectionAgentRun): string {
  const answer = run.result?.answer
  return typeof answer === 'string' && answer.trim() ? answer : ''
}

function agentRunConflicts(run: CollectionAgentRun): Array<{ title: string; existing: string; proposed: string; reason: string }> {
  const raw = run.result?.conflicts
  if (!Array.isArray(raw)) return []
  return raw
    .filter((item) => typeof item === 'object' && item !== null)
    .map((item) => {
      const value = item as Record<string, unknown>
      return {
        title: String(value.title || 'Canon 冲突'),
        existing: String(value.existing || ''),
        proposed: String(value.proposed || ''),
        reason: String(value.reason || ''),
      }
    })
}

function agentRunMessage(run: CollectionAgentRun): string {
  const message = run.request?.message
  return typeof message === 'string' ? message : ''
}

function agentRunTaskLabel(run: CollectionAgentRun): string {
  const taskType = typeof run.request?.task_type === 'string' ? run.request.task_type : 'free_chat'
  const quickTask = agentQuickTasks.value.find((task) => task.kind === taskType)
  if (quickTask) return quickTask.title
  return agentCopy.value.freeChat
}

function agentRunTimeLabel(run: CollectionAgentRun): string {
  const raw = run.completed_at || run.updated_at || run.created_at
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleString()
}

function agentRunVisibleAnswer(run: CollectionAgentRun): string {
  const answer = agentRunAnswer(run)
  if (!agentCollapsedRunIds.value.includes(run.id)) return answer
  return `${answer.slice(0, AGENT_LONG_ANSWER_THRESHOLD).trim()}...`
}

function agentRunCanCollapse(run: CollectionAgentRun): boolean {
  return agentRunAnswer(run).length > AGENT_LONG_ANSWER_THRESHOLD
}

function toggleAgentRunCollapsed(run: CollectionAgentRun) {
  if (!agentRunCanCollapse(run)) return
  if (agentCollapsedRunIds.value.includes(run.id)) {
    agentCollapsedRunIds.value = agentCollapsedRunIds.value.filter((id) => id !== run.id)
    if (!agentExpandedRunIds.value.includes(run.id)) {
      agentExpandedRunIds.value = [...agentExpandedRunIds.value, run.id]
    }
  } else {
    agentCollapsedRunIds.value = [...agentCollapsedRunIds.value, run.id]
    agentExpandedRunIds.value = agentExpandedRunIds.value.filter((id) => id !== run.id)
  }
}

async function scrollToAgentRun(runId: string) {
  await nextTick()
  const target = document.getElementById(`collection-agent-run-${runId}`)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    agentHighlightedRunId.value = runId
    window.setTimeout(() => {
      if (agentHighlightedRunId.value === runId) agentHighlightedRunId.value = null
    }, 1800)
  }
}

function articlePreview(body: string): string {
  const compact = body.trim().replace(/\s+/g, ' ')
  return compact.slice(0, 140) || t('collections.emptyArticle')
}

function outlineTypeLabel(type: OutlineItemType): string {
  return typeLabelForProject(type, projectType.value, locale.value)
}

function outlineStatusLabel(status: OutlineItemStatus): string {
  return outlineStatusOptions.value.find((item) => item.value === status)?.label ?? status
}

function outlineStatusTone(status: OutlineItemStatus): string {
  if (status === 'done') return 'bg-emerald-50 text-emerald-700 ring-emerald-100'
  if (status === 'drafting') return 'bg-blue-50 text-blue-700 ring-blue-100'
  if (status === 'revising') return 'bg-violet-50 text-violet-700 ring-violet-100'
  if (status === 'parked') return 'bg-stone-100 text-stone-500 ring-stone-200'
  return 'bg-amber-50 text-amber-700 ring-amber-100'
}

function nodeTitle(node: ManuscriptTreeNode): string {
  if (node.item.title) return node.item.title
  if (node.item.entry_id) return articleTitleForId(node.item.entry_id, store.articles)
  return t('collectionOutline.untitled')
}

function defaultTitleForType(type: OutlineItemType): string {
  if (type === 'part') return `${projectLabels.value.part}：`
  if (type === 'chapter') return `${projectLabels.value.chapter}：`
  if (type === 'scene') return `${projectLabels.value.scene}：`
  return `${projectLabels.value.note}：`
}

async function openCreateDialog() {
  newTitle.value = ''
  newDescription.value = ''
  newProjectType.value = 'general'
  createDialogOpen.value = true
}

async function createCollection() {
  if (!newTitle.value.trim()) return
  actionError.value = null
  try {
    await store.createCollection(newTitle.value.trim(), newDescription.value.trim(), newProjectType.value)
    createDialogOpen.value = false
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

async function saveCollectionMeta() {
  const saved = await saveCollectionMetaIfNeeded()
  if (saved) collectionMetaEditing.value = false
}

function editCollectionMeta() {
  collectionMetaEditing.value = true
  collectionActionsOpen.value = false
}

function cancelCollectionMetaEdit() {
  const collection = store.selectedCollection
  draftTitle.value = collection?.title ?? ''
  draftDescription.value = collection?.description ?? ''
  draftProjectType.value = collectionProjectType(collection)
  collectionMetaEditing.value = false
  actionError.value = null
}

async function saveCollectionMetaIfNeeded(): Promise<boolean> {
  actionError.value = null
  if (!store.selectedCollection) return true
  if (!draftTitle.value.trim()) {
    actionError.value = t('collections.titleRequired')
    return false
  }
  if (
    draftTitle.value.trim() === store.selectedCollection.title
    && draftDescription.value.trim() === store.selectedCollection.description
    && draftProjectType.value === collectionProjectType(store.selectedCollection)
  ) {
    return true
  }
  savingMeta.value = true
  try {
    await store.updateCollection(
      store.selectedCollection.id,
      draftTitle.value.trim(),
      draftDescription.value.trim(),
      draftProjectType.value,
    )
    return true
  } catch (e) {
    actionError.value = errorMessage(e)
    return false
  } finally {
    savingMeta.value = false
  }
}

function loadOutlineDraft(item: CollectionOutlineItem | null) {
  outlineActionError.value = null
  outlineDraftTitle.value = item?.title ?? ''
  outlineDraftType.value = item?.item_type ?? articleTypeForProject(projectType.value)
  outlineDraftStatus.value = item?.status ?? 'idea'
  outlineDraftParentId.value = item?.parent_id ?? ''
  outlineDraftSummary.value = item?.summary ?? ''
  outlineDraftNotes.value = item?.notes ?? ''
  outlineDraftEntryId.value = item?.entry_id ?? ''
  outlineDraftPov.value = item?.pov ?? ''
  outlineDraftSetting.value = item?.setting ?? ''
  outlineDraftTimeline.value = item?.timeline ?? ''
  outlineDraftTags.value = item?.tags.join(', ') ?? ''
  outlineDraftTargetWords.value = item?.target_word_count ?? null
}

function outlinePayload(): CollectionOutlineItemInput {
  const tags = outlineDraftTags.value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
  return {
    parent_id: outlineDraftParentId.value || null,
    title: outlineDraftTitle.value.trim() || t('collectionOutline.untitled'),
    item_type: outlineDraftType.value,
    status: outlineDraftStatus.value,
    summary: outlineDraftSummary.value,
    notes: outlineDraftNotes.value,
    entry_id: outlineDraftEntryId.value || null,
    pov: outlineDraftPov.value,
    setting: outlineDraftSetting.value,
    timeline: outlineDraftTimeline.value,
    tags,
    target_word_count: outlineDraftTargetWords.value && outlineDraftTargetWords.value > 0
      ? outlineDraftTargetWords.value
      : null,
  }
}

function payloadFromItem(
  item: CollectionOutlineItem,
  patch: Partial<CollectionOutlineItemInput>,
): CollectionOutlineItemInput {
  return {
    parent_id: item.parent_id,
    entry_id: item.entry_id,
    title: item.title,
    item_type: item.item_type,
    status: item.status,
    summary: item.summary,
    notes: item.notes,
    pov: item.pov,
    setting: item.setting,
    timeline: item.timeline,
    tags: item.tags,
    target_word_count: item.target_word_count,
    ...patch,
  }
}

async function createOutlineItem(type: OutlineItemType = articleTypeForProject(projectType.value), parentId: string | null = null) {
  if (!store.selectedCollection) return
  outlineActionError.value = null
  try {
    const created = await store.createOutlineItem({
      title: defaultTitleForType(type),
      item_type: type,
      status: 'idea',
      parent_id: parentId,
    })
    if (created) {
      store.selectOutlineItem(created.id)
      loadOutlineDraft(created)
      viewMode.value = 'structure'
      outlineEditing.value = true
      outlineAdvancedOpen.value = false
      outlineCreateMenuOpen.value = false
    }
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  }
}

async function createChildOutlineItem() {
  const parent = store.selectedOutlineItem
  const type = defaultChildType(parent?.item_type ?? null, projectType.value)
  await createOutlineItem(type, parent?.id ?? null)
}

async function createSiblingOutlineItem() {
  const selected = store.selectedOutlineItem
  await createOutlineItem(selected?.item_type ?? defaultChildType(null, projectType.value), selected?.parent_id ?? null)
}

async function createNodeFromArticle(article: CollectionArticle, parentId: string | null = store.selectedOutlineItemId) {
  if (!store.selectedCollection) return
  outlineActionError.value = null
  try {
    const created = await store.createOutlineItem({
      title: article.title || t('articles.untitled'),
      item_type: articleTypeForProject(projectType.value),
      status: article.body.trim() ? 'drafting' : 'idea',
      entry_id: article.id,
      parent_id: parentId,
      target_word_count: article.word_count || null,
    })
    if (created) {
      store.selectOutlineItem(created.id)
      viewMode.value = 'structure'
    }
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  }
}

async function saveOutlineItem() {
  if (!store.selectedOutlineItem) return
  const payload = outlinePayload()
  if (!canUseParent(store.outline, store.selectedOutlineItem.id, payload.parent_id ?? null)) {
    outlineActionError.value = t('collectionOutline.parentCycleError')
    return
  }
  outlineSaving.value = true
  outlineActionError.value = null
  try {
    await store.updateOutlineItem(store.selectedOutlineItem.id, payload)
    if (payload.entry_id && !store.articles.some((article) => article.id === payload.entry_id)) {
      await store.addArticles([payload.entry_id])
      await store.loadOutline()
    }
    outlineEditing.value = false
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  } finally {
    outlineSaving.value = false
  }
}

function editOutlineItem() {
  if (!store.selectedOutlineItem) return
  loadOutlineDraft(store.selectedOutlineItem)
  outlineEditing.value = true
  outlineAdvancedOpen.value = false
}

function cancelOutlineEdit() {
  loadOutlineDraft(store.selectedOutlineItem)
  outlineEditing.value = false
  outlineAdvancedOpen.value = false
}

async function saveOutlineItemIfDirty(): Promise<boolean> {
  if (!store.selectedOutlineItem) return true
  const payload = outlinePayload()
  const current = store.selectedOutlineItem
  const dirty = payload.title !== current.title
    || payload.item_type !== current.item_type
    || payload.status !== current.status
    || payload.summary !== current.summary
    || payload.notes !== current.notes
    || (payload.parent_id ?? null) !== current.parent_id
    || (payload.entry_id ?? null) !== current.entry_id
    || payload.pov !== current.pov
    || payload.setting !== current.setting
    || payload.timeline !== current.timeline
    || (payload.target_word_count ?? null) !== current.target_word_count
    || payload.tags?.join(', ') !== current.tags.join(', ')
  if (!dirty) return true
  await saveOutlineItem()
  return !outlineActionError.value
}

async function selectOutlineItem(id: string) {
  const saved = await saveOutlineItemIfDirty()
  if (!saved) return
  setCollectionArticleHighlight(null)
  store.selectOutlineItem(id)
  outlineEditing.value = false
  outlineAdvancedOpen.value = false
  await nextTick()
  scrollToOutlineItem(id)
}

async function deleteSelectedOutlineItem() {
  if (!store.selectedOutlineItem) return
  if (!confirm(t('collectionOutline.deleteConfirm'))) return
  try {
    await store.deleteOutlineItem(store.selectedOutlineItem.id)
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  }
}

async function moveOutlineItem(itemId: string, direction: -1 | 1) {
  const item = store.outline.find((row) => row.id === itemId)
  if (!item) return
  const global = [...store.outline].sort((a, b) => a.sort_order - b.sort_order)
  const siblings = global.filter((row) => (row.parent_id ?? null) === (item.parent_id ?? null))
  const index = siblings.findIndex((row) => row.id === itemId)
  const next = siblings[index + direction]
  if (index < 0 || !next) return
  const ids = global.map((row) => row.id)
  const from = ids.indexOf(item.id)
  const to = ids.indexOf(next.id)
  const [moving] = ids.splice(from, 1)
  ids.splice(to, 0, moving)
  try {
    await store.reorderOutline(ids)
  } catch {
    // Store owns visible error state.
  }
}

async function changeOutlineParent(item: CollectionOutlineItem, parentId: string | null) {
  if (!canUseParent(store.outline, item.id, parentId)) {
    outlineActionError.value = t('collectionOutline.parentCycleError')
    return
  }
  try {
    await store.updateOutlineItem(item.id, payloadFromItem(item, { parent_id: parentId }))
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  }
}

function onOutlineDragStart(itemId: string) {
  dragOutlineItemId.value = itemId
}

async function onOutlineDrop(targetId: string) {
  const movingId = dragOutlineItemId.value
  dragOutlineItemId.value = null
  if (!movingId || movingId === targetId) return
  const moving = store.outline.find((item) => item.id === movingId)
  const target = store.outline.find((item) => item.id === targetId)
  if (!moving || !target) return
  await changeOutlineParent(moving, target.parent_id ?? null)
  const global = [...store.outline].sort((a, b) => a.sort_order - b.sort_order).map((item) => item.id)
  const from = global.indexOf(movingId)
  const to = global.indexOf(targetId)
  if (from < 0 || to < 0) return
  const [row] = global.splice(from, 1)
  global.splice(to, 0, row)
  await store.reorderOutline(global)
}

async function createArticleFromOutline() {
  if (!store.selectedOutlineItem) return
  const saved = await saveOutlineItemIfDirty()
  if (!saved) return
  try {
    const article = await articlesApi.create({
      title: outlineDraftTitle.value.trim() || t('articles.untitled'),
      body: outlineDraftSummary.value.trim(),
      tags: outlineDraftTags.value.split(',').map((tag) => tag.trim()).filter(Boolean),
    })
    allArticles.value = [article, ...allArticles.value]
    if (!store.articles.some((item) => item.id === article.id)) {
      await store.addArticles([article.id])
    }
    outlineDraftEntryId.value = article.id
    await saveOutlineItem()
  } catch (e) {
    outlineActionError.value = errorMessage(e)
  }
}

async function openLinkedOutlineArticle() {
  if (!store.selectedOutlineItem?.entry_id) return
  await router.push({
    name: 'articles',
    query: { id: store.selectedOutlineItem.entry_id },
  })
}

async function openArticlePicker() {
  if (!store.selectedCollection) return
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  try {
    actionError.value = null
    allArticles.value = await articlesApi.listArticles(500)
  } catch (e) {
    actionError.value = errorMessage(e)
    return
  }
  selectedArticleIds.value = []
  articlePickerOpen.value = true
}

function togglePickArticle(entryId: string) {
  if (currentArticleIds.value.has(entryId)) return
  if (selectedArticleIds.value.includes(entryId)) {
    selectedArticleIds.value = selectedArticleIds.value.filter((id) => id !== entryId)
  } else {
    selectedArticleIds.value = [...selectedArticleIds.value, entryId]
  }
}

async function addSelectedArticles() {
  if (!selectedArticleIds.value.length) return
  try {
    actionError.value = null
    await store.addArticles(selectedArticleIds.value)
    articlePickerOpen.value = false
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

async function removeUnplannedArticle(entryId: string) {
  if (!confirm(t('collections.confirmRemoveArticle'))) return
  try {
    await store.removeArticle(entryId)
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

async function selectCollection(id: string) {
  const token = ++collectionSelectionToken
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved || token !== collectionSelectionToken) return
  await store.selectCollection(id)
}

async function deleteSelectedCollection() {
  if (!store.selectedCollection) return
  collectionActionsOpen.value = false
  if (!confirm(t('collections.confirmDeleteCollection'))) return
  try {
    await store.deleteCollection(store.selectedCollection.id)
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

async function exportSelected(format: 'md' | 'txt' | 'docx') {
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  await store.exportSelected(format)
}

function safeCollectionFilename(title: string, suffix: string): string {
  const safe = (title || t('collections.untitled')).replace(/[<>:"/\\|?*]/g, '').trim() || 'collection'
  return `${safe}.${suffix}`
}

async function exportOutlineMarkdown() {
  if (!store.selectedCollection) return
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved || !store.selectedCollection) return
  outlineExporting.value = true
  outlineActionError.value = null
  try {
    const markdown = buildOutlineMarkdown({
      collectionTitle: store.selectedCollection.title,
      collectionDescription: store.selectedCollection.description,
      outline: filteredOutline.value,
      typeLabel: outlineTypeLabel,
      statusLabel: outlineStatusLabel,
      articleTitleForId: (entryId) =>
        allArticles.value.find((article) => article.id === entryId)?.title
        || store.articles.find((article) => article.id === entryId)?.title
        || entryId,
    })
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    await import('../../utils/exportFile').then(({ saveBlobWithDialog }) =>
      saveBlobWithDialog(blob, safeCollectionFilename(`${store.selectedCollection?.title || 'collection'}-planning`, 'md'), 'md')
    )
  } catch (e) {
    outlineActionError.value = `导出大纲失败：${errorMessage(e)}`
  } finally {
    outlineExporting.value = false
  }
}

function closeDeleteContextMenu() {
  deleteContextMenuOpen.value = false
  deleteContextTarget.value = null
}

function openDeleteContextMenu(event: MouseEvent, target: typeof deleteContextTarget.value) {
  if (!target) return
  event.preventDefault()
  deleteContextTarget.value = target
  deleteContextMenuX.value = Math.max(12, Math.min(event.clientX + 8, window.innerWidth - 172))
  deleteContextMenuY.value = Math.max(12, Math.min(event.clientY + 8, window.innerHeight - 56))
  deleteContextMenuOpen.value = true
}

function handleDeleteContextMenuSelect(item: { key: string }) {
  const target = deleteContextTarget.value
  closeDeleteContextMenu()
  if (item.key !== 'delete' || !target) return
  if (store.selectedCollectionId === target.id) {
    void deleteSelectedCollection()
    return
  }
  void selectCollection(target.id).then(() => deleteSelectedCollection())
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f5f1e8] text-stone-900">
    <aside
      class="flex shrink-0 flex-col border-r border-stone-200 bg-[#2d2a25] text-stone-100"
      :style="collectionListPaneStyle"
      data-testid="collections-list-pane"
      data-tour="collections-list"
    >
      <div class="border-b border-white/10 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-[0.28em] text-stone-400">{{ t('collections.shelf') }}</p>
            <h2 class="mt-1 text-lg font-semibold">{{ t('collections.title') }}</h2>
          </div>
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-200 text-xl font-semibold text-stone-900 hover:bg-amber-100"
            data-tour="collections-create"
            :title="t('collections.newCollection')"
            :aria-label="t('collections.newCollection')"
            @click="openCreateDialog"
          >
            +
          </button>
        </div>
        <p class="mt-2 text-xs text-stone-400">
          {{ t('collections.total', { count: store.collections.length }) }}
        </p>
        <input
          v-model="collectionSearch"
          type="search"
          class="mt-3 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-stone-500 focus:border-amber-200/60"
          :placeholder="t('collections.searchPlaceholder')"
        />
      </div>

      <div class="flex-1 space-y-2 overflow-y-auto p-3">
        <div v-if="store.loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-300">{{ store.error }}</div>
        <div v-else-if="!store.collections.length" class="p-4 text-sm text-stone-400">
          {{ t('collections.emptyCollections') }}
        </div>
        <div v-else-if="!filteredCollections.length" class="p-4 text-sm text-stone-400">
          {{ t('collections.noSearchResults') }}
        </div>
        <button
          v-for="collection in filteredCollections"
          :key="collection.id"
          :class="[
            'w-full rounded-lg px-3 py-3 text-left transition-all',
            store.selectedCollectionId === collection.id
              ? 'bg-amber-100 text-stone-950 shadow-sm'
              : 'bg-white/5 text-stone-200 hover:bg-white/10'
          ]"
          @click="selectCollection(collection.id)"
          @contextmenu="openDeleteContextMenu($event, { kind: 'collection', id: collection.id })"
        >
          <div class="truncate font-semibold leading-snug">{{ collection.title || t('collections.untitled') }}</div>
          <div v-if="store.selectedCollectionId === collection.id" class="mt-1 line-clamp-1 text-xs opacity-70">
            {{ collection.description || t('collections.noDescription') }}
          </div>
          <div class="mt-2 flex flex-wrap gap-2 text-[11px] opacity-70">
            <span>{{ projectTypeLabel(collection.project_type, locale) }}</span>
            <span>{{ t('collections.articleCount', { count: collection.article_count }) }}</span>
          </div>
        </button>
      </div>
    </aside>
    <PaneResizeHandle data-testid="collections-list-resizer" @pointerdown="collectionListPane.startResize" />

    <main class="flex min-w-0 flex-1 flex-col">
      <header class="border-b border-stone-200 bg-[#fbf7ef]/95 px-6 py-3">
        <template v-if="store.selectedCollection">
          <div data-tour="collections-header">
            <div v-if="collectionMetaEditing" class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto] lg:items-start">
              <div class="space-y-2">
                <input
                  v-model="draftTitle"
                  data-testid="collection-title-input"
                  class="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-xl font-semibold outline-none focus:ring-2 focus:ring-amber-200"
                  :placeholder="t('collections.titlePlaceholder')"
                />
                <textarea
                  v-model="draftDescription"
                  rows="2"
                  class="w-full resize-none rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm leading-6 text-stone-600 outline-none focus:ring-2 focus:ring-amber-200"
                  :placeholder="t('collections.descriptionPlaceholder')"
                />
              </div>
              <label class="block" data-tour="collections-project-type">
                <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.projectType') }}</span>
                <select v-model="draftProjectType" class="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-200">
                  <option v-for="option in projectTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
              </label>
              <div class="flex gap-2 lg:pt-5">
                <button class="rounded-lg bg-stone-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" :disabled="savingMeta" @click="saveCollectionMeta">
                  {{ savingMeta ? t('common.saving') : t('common.save') }}
                </button>
                <button class="rounded-lg bg-white px-3 py-2 text-sm text-stone-600 ring-1 ring-stone-200" @click="cancelCollectionMetaEdit">
                  {{ t('common.cancel') }}
                </button>
              </div>
            </div>
            <div v-else class="flex min-w-0 items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <h1 class="truncate text-2xl font-semibold tracking-tight text-stone-950">{{ store.selectedCollection.title || t('collections.untitled') }}</h1>
                  <span class="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-stone-600 ring-1 ring-stone-200" data-tour="collections-project-type">
                    {{ projectTypeLabel(projectType, locale) }}
                  </span>
                </div>
                <p class="mt-1 line-clamp-1 text-sm text-stone-600">{{ store.selectedCollection.description || t('collections.noDescription') }}</p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <button
                  class="rounded-lg bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
                  data-tour="collections-add-articles"
                  @click="openArticlePicker"
                >
                  {{ t('collections.addArticles') }}
                </button>
                <button
                  data-testid="collection-edit-meta"
                  class="rounded-lg bg-white px-3 py-2 text-sm font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
                  @click="editCollectionMeta"
                >
                  {{ t('collections.editInfo') }}
                </button>
                <div class="relative">
                  <button
                    class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-lg text-stone-600 ring-1 ring-stone-200 hover:bg-stone-50"
                    :title="t('collections.moreActions')"
                    :aria-label="t('collections.moreActions')"
                    @click="collectionActionsOpen = !collectionActionsOpen"
                  >
                    ⋯
                  </button>
                  <div v-if="collectionActionsOpen" class="absolute right-0 z-30 mt-2 w-40 rounded-lg border border-stone-200 bg-white p-1 shadow-xl">
                    <button class="w-full rounded-md px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50" @click="deleteSelectedCollection">
                      {{ t('collections.deleteCollection') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="!collectionMetaEditing" class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-stone-200/80 pt-3">
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-stone-600">
                <span>{{ t('collections.articleCount', { count: store.articles.length }) }}</span>
                <span>{{ t('collectionOutline.itemCount', { count: store.outline.length }) }}</span>
                <span>{{ t('collectionOutline.linkedCompact', { linked: outlineProgress.linkedItems, total: outlineProgress.totalItems }) }}</span>
                <span>{{ t('collectionOutline.wordsCompact', { current: outlineProgress.linkedArticleWordCount, target: outlineProgress.targetWordTotal || '—' }) }}</span>
                <span v-if="outlineProgressPercent !== null">{{ outlineProgressPercent }}%</span>
              </div>
              <div class="inline-flex rounded-lg bg-stone-100 p-1 text-sm font-semibold text-stone-600" data-tour="collections-tabs">
                <button type="button" data-tour="collection-agent-tab" :class="['rounded-md px-3 py-1.5 transition', viewMode === 'structure' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900']" @click="viewMode = 'structure'">
                  {{ structureTabLabel(locale) }}
                </button>
                <button type="button" :class="['rounded-md px-3 py-1.5 transition', viewMode === 'board' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900']" @click="viewMode = 'board'">
                  {{ boardTabLabel(locale) }}
                </button>
                <button type="button" :class="['rounded-md px-3 py-1.5 transition', viewMode === 'export' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900']" @click="viewMode = 'export'">
                  {{ exportTabLabel(locale) }}
                </button>
                <button type="button" :class="['rounded-md px-3 py-1.5 transition', viewMode === 'agent' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900']" @click="viewMode = 'agent'">
                  Agent
                </button>
              </div>
            </div>
          </div>
          <p v-if="store.exportMessage" class="mt-3 text-sm text-emerald-700">
            {{ store.exportMessage }}
          </p>
          <p v-if="actionError || store.error" class="mt-3 text-sm text-red-700">
            {{ actionError || store.error }}
          </p>
        </template>
        <div v-else class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-semibold">{{ t('collections.selectCollection') }}</h1>
            <p class="mt-2 text-sm text-stone-500">{{ t('collections.selectHint') }}</p>
          </div>
          <button
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white"
            @click="openCreateDialog"
          >
            {{ t('collections.newCollection') }}
          </button>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 overflow-hidden">
        <template v-if="viewMode === 'structure'">
          <section
            class="shrink-0 overflow-y-auto border-r border-stone-200 bg-[#fbf7ef] p-4"
            :style="structurePaneStyle"
            data-testid="collection-outline-pane"
            data-tour="collections-structure"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold text-stone-900">{{ t('collectionOutline.structureTitle') }}</h3>
                <p class="mt-0.5 text-xs text-stone-600">{{ t('collectionOutline.structureCount', { count: store.outline.length }) }}</p>
              </div>
              <div class="relative flex items-center gap-1" data-tour="outline-create-buttons">
                <button
                  class="rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                  @click="createOutlineItem(defaultChildType(null, projectType), null)"
                >
                  + {{ t('collectionOutline.newTopLevel') }}
                </button>
                <button
                  class="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-xs text-stone-600 ring-1 ring-stone-200 hover:bg-stone-50"
                  :title="t('collectionOutline.chooseType')"
                  :aria-label="t('collectionOutline.chooseType')"
                  @click="outlineCreateMenuOpen = !outlineCreateMenuOpen"
                >
                  ▾
                </button>
                <div v-if="outlineCreateMenuOpen" class="absolute right-0 top-10 z-30 w-44 rounded-lg border border-stone-200 bg-white p-1 shadow-xl">
                  <button
                    v-for="option in outlineTypeOptions"
                    :key="option.value"
                    class="w-full rounded-md px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-50"
                    @click="createOutlineItem(option.value, null)"
                  >
                    + {{ option.label }}
                  </button>
                </div>
              </div>
            </div>
            <div class="mb-3">
              <button class="text-xs font-semibold text-stone-600 hover:text-stone-800" @click="structureGuideOpen = !structureGuideOpen">
                {{ structureGuideOpen ? '⌄' : '›' }} {{ t('collectionOutline.structureGuide') }}
              </button>
              <p v-if="structureGuideOpen" class="mt-2 rounded-lg bg-white px-3 py-2 text-xs leading-5 text-stone-600 ring-1 ring-stone-200">
                {{ t('collectionOutline.structureRule') }}
              </p>
            </div>

            <div v-if="outlineActionError || store.error" class="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
              {{ outlineActionError || store.error }}
            </div>
            <div v-if="store.outlineLoading" class="rounded-xl bg-white/70 p-4 text-sm text-stone-600">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!store.outline.length" class="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-6 text-center">
              <div class="text-sm font-semibold text-stone-700">{{ t('collectionOutline.emptyTitle') }}</div>
              <p class="mt-2 text-xs leading-5 text-stone-500">{{ t('collectionOutline.emptyStructureHint') }}</p>
            </div>
            <div v-else class="space-y-1.5" data-tour="manuscript-tree">
              <article
                v-for="node in flatTree"
                :key="node.item.id"
                draggable="true"
                :style="{ paddingLeft: `${12 + node.depth * 18}px` }"
                :data-outline-item-id="node.item.id"
                :data-collection-article-id="node.item.entry_id || undefined"
                :class="[
                  'group cursor-pointer rounded-lg border bg-white py-2.5 pr-2.5 shadow-sm transition-all',
                  store.selectedOutlineItemId === node.item.id
                    ? 'border-amber-400 ring-2 ring-amber-200 shadow-md'
                    : highlightedCollectionArticleId === node.item.entry_id
                    ? 'border-amber-300 ring-1 ring-amber-100'
                    : 'border-stone-200 hover:border-stone-300 hover:shadow-md'
                ]"
                @click="selectOutlineItem(node.item.id)"
                @dragstart="onOutlineDragStart(node.item.id)"
                @dragover.prevent
                @drop="onOutlineDrop(node.item.id)"
              >
                <div class="flex items-start gap-3">
                  <div class="w-8 shrink-0 rounded-md bg-stone-100 py-1 text-center text-[11px] font-semibold text-stone-500">
                    {{ node.path.join('.') }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <h4 class="min-w-0 truncate font-semibold text-stone-900">{{ nodeTitle(node) }}</h4>
                      <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-700">
                        {{ outlineTypeLabel(node.item.item_type) }}
                      </span>
                      <span :class="['rounded-full px-2 py-0.5 text-[11px] ring-1', outlineStatusTone(node.item.status)]">
                        {{ outlineStatusLabel(node.item.status) }}
                      </span>
                    </div>
                    <p class="mt-1 line-clamp-1 text-xs leading-5 text-stone-500">
                      {{ node.item.summary || t('collectionOutline.noSummary') }}
                    </p>
                    <div class="mt-1.5 flex flex-wrap gap-1.5">
                      <span v-if="node.item.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                        {{ t('collectionOutline.linked') }}
                      </span>
                      <span v-if="node.children.length" class="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-500">
                        {{ t('collectionOutline.childCount', { count: node.children.length }) }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="mt-2 flex flex-wrap justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="moveOutlineItem(node.item.id, -1)"
                  >
                    ↑
                  </button>
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="moveOutlineItem(node.item.id, 1)"
                  >
                    ↓
                  </button>
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="createOutlineItem(defaultChildType(node.item.item_type, projectType), node.item.id)"
                  >
                    {{ t('collectionOutline.newChild') }}
                  </button>
                </div>
              </article>
            </div>

            <div class="mt-5 rounded-2xl border border-stone-200 bg-white/80 p-4" data-tour="unplanned-articles">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold text-stone-900">{{ t('collectionOutline.unplannedTitle') }}</h4>
                  <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('collectionOutline.unplannedHelp') }}</p>
                </div>
                <button class="rounded-xl bg-stone-100 px-3 py-2 text-xs text-stone-700" @click="openArticlePicker">
                  {{ t('collections.addArticles') }}
                </button>
              </div>
              <div v-if="!unplanned.length" class="mt-4 rounded-xl border border-dashed border-stone-200 p-4 text-center text-xs text-stone-600">
                {{ t('collectionOutline.noUnplanned') }}
              </div>
              <div v-else class="mt-4 space-y-2">
                <article
                  v-for="article in unplanned"
                  :key="article.id"
                  :data-collection-article-id="article.id"
                  :class="[
                    'rounded-xl border bg-white p-3',
                    highlightedCollectionArticleId === article.id ? 'border-amber-400 ring-2 ring-amber-200' : 'border-stone-200'
                  ]"
                >
                  <div class="font-semibold text-sm text-stone-900">{{ article.title || t('articles.untitled') }}</div>
                  <p class="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{{ articlePreview(article.body) }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button
                      class="rounded-lg bg-stone-900 px-2 py-1 text-xs font-semibold text-white"
                      @click="createNodeFromArticle(article, store.selectedOutlineItemId)"
                    >
                      {{ store.selectedOutlineItem ? t('collectionOutline.placeUnderSelected') : t('collectionOutline.placeTopLevel') }}
                    </button>
                    <button class="rounded-lg bg-stone-100 px-2 py-1 text-xs text-stone-600" @click="removeUnplannedArticle(article.id)">
                      {{ t('collectionOutline.removeFromCollection') }}
                    </button>
                  </div>
                </article>
              </div>
            </div>
          </section>
          <PaneResizeHandle data-testid="collections-outline-resizer" @pointerdown="structurePane.startResize" />

          <section class="flex-1 overflow-y-auto p-6" data-testid="collection-outline-detail">
            <div v-if="store.selectedOutlineItem" class="mx-auto max-w-4xl space-y-5">
              <div v-if="!outlineEditing" class="rounded-xl border border-stone-200 bg-white p-6 shadow-sm" data-testid="collection-outline-reader">
                <div class="flex flex-col gap-4 min-[1280px]:flex-row min-[1280px]:items-start min-[1280px]:justify-between">
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">{{ outlineTypeLabel(store.selectedOutlineItem.item_type) }}</span>
                      <span :class="['rounded-full px-2 py-0.5 text-xs ring-1', outlineStatusTone(store.selectedOutlineItem.status)]">{{ outlineStatusLabel(store.selectedOutlineItem.status) }}</span>
                      <span v-if="store.selectedOutlineItem.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">{{ t('collectionOutline.linked') }}</span>
                    </div>
                    <h3 class="mt-3 text-2xl font-semibold text-stone-950">{{ store.selectedOutlineItem.title || t('collectionOutline.untitled') }}</h3>
                    <p class="mt-3 max-w-3xl whitespace-pre-wrap text-sm leading-7 text-stone-600">
                      {{ store.selectedOutlineItem.summary || t('collectionOutline.noSummary') }}
                    </p>
                  </div>
                  <div class="flex flex-wrap justify-start gap-2 min-[1280px]:justify-end">
                    <button class="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createSiblingOutlineItem">
                      {{ t('collectionOutline.newSibling') }}
                    </button>
                    <button class="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700" data-tour="outline-new-child" @click="createChildOutlineItem">
                      {{ t('collectionOutline.newChild') }}
                    </button>
                    <button data-testid="outline-edit-details" class="rounded-lg bg-stone-900 px-3 py-2 text-sm font-semibold text-white" @click="editOutlineItem">
                      {{ t('collectionOutline.editDetails') }}
                    </button>
                  </div>
                </div>
                <div class="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-stone-100 pt-4 text-sm text-stone-600">
                  <span v-if="store.selectedOutlineItem.pov"><strong class="text-stone-400">{{ t('collectionOutline.fieldPov') }}：</strong>{{ store.selectedOutlineItem.pov }}</span>
                  <span v-if="store.selectedOutlineItem.timeline"><strong class="text-stone-400">{{ t('collectionOutline.fieldTimeline') }}：</strong>{{ store.selectedOutlineItem.timeline }}</span>
                  <span v-if="store.selectedOutlineItem.setting"><strong class="text-stone-400">{{ t('collectionOutline.fieldSetting') }}：</strong>{{ store.selectedOutlineItem.setting }}</span>
                  <span v-if="store.selectedOutlineItem.target_word_count"><strong class="text-stone-400">{{ t('collectionOutline.fieldTargetWords') }}：</strong>{{ store.selectedOutlineItem.target_word_count }}</span>
                </div>
                <div v-if="store.selectedOutlineItem.tags.length" class="mt-4 flex flex-wrap gap-2">
                  <span v-for="tag in store.selectedOutlineItem.tags" :key="tag" class="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-600">{{ tag }}</span>
                </div>
                <div v-if="store.selectedOutlineItem.notes" class="mt-5 rounded-lg bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                  <div class="mb-1 text-xs font-semibold text-amber-700">{{ t('collectionOutline.fieldNotes') }}</div>
                  <p class="whitespace-pre-wrap">{{ store.selectedOutlineItem.notes }}</p>
                </div>
              </div>

              <div v-else class="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
                <div class="mb-5 flex items-start justify-between gap-4">
                  <div>
                    <h3 class="text-xl font-semibold text-stone-900">{{ t('collectionOutline.editDetails') }}</h3>
                    <p class="mt-1 text-sm text-stone-500">{{ store.selectedOutlineItem.title || t('collectionOutline.untitled') }}</p>
                  </div>
                  <div class="flex flex-wrap justify-end gap-2">
                    <button class="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="cancelOutlineEdit">
                      {{ t('common.cancel') }}
                    </button>
                    <button class="rounded-lg bg-stone-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" :disabled="outlineSaving" @click="saveOutlineItem">
                      {{ outlineSaving ? t('common.saving') : t('common.save') }}
                    </button>
                  </div>
                </div>

                <div class="grid gap-4 md:grid-cols-2" data-tour="outline-detail-fields">
                  <label class="md:col-span-2" data-tour="outline-title-field">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTitle') }}</span>
                    <input v-model="outlineDraftTitle" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldTitleHelp') }}</span>
                  </label>
                  <label data-tour="outline-type-field">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldType') }}</span>
                    <select v-model="outlineDraftType" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldTypeHelp') }}</span>
                    <span class="mt-2 block rounded-xl bg-indigo-50 px-3 py-2 text-xs leading-5 text-indigo-800">{{ outlineTypeGuide }}</span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldParent') }}</span>
                    <select v-model="outlineDraftParentId" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option value="">{{ t('collectionOutline.noParent') }}</option>
                      <option v-for="node in parentOptions" :key="node.item.id" :value="node.item.id">
                        {{ '　'.repeat(node.depth) }}{{ node.path.join('.') }} {{ nodeTitle(node) }}
                      </option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">
                      {{ selectedParent ? t('collectionOutline.currentParent', { title: selectedParent.title }) : t('collectionOutline.parentHelp') }}
                    </span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldStatus') }}</span>
                    <select v-model="outlineDraftStatus" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label data-tour="outline-linked-article">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldEntry') }}</span>
                    <select v-model="outlineDraftEntryId" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option value="">{{ t('collectionOutline.noLinkedArticle') }}</option>
                      <option v-for="article in allArticles" :key="article.id" :value="article.id">
                        {{ article.title || t('articles.untitled') }}
                      </option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldEntryHelp') }}</span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTargetWords') }}</span>
                    <input v-model.number="outlineDraftTargetWords" type="number" min="0" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label class="md:col-span-2">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldSummary') }}</span>
                    <textarea v-model="outlineDraftSummary" rows="4" class="w-full resize-none rounded-xl border border-stone-200 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldPov') }}</span>
                    <input v-model="outlineDraftPov" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.fieldPovPlaceholder')" />
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldPovHelp') }}</span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTimeline') }}</span>
                    <input v-model="outlineDraftTimeline" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldSetting') }}</span>
                    <input v-model="outlineDraftSetting" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTags') }}</span>
                    <input v-model="outlineDraftTags" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.tagsPlaceholder')" />
                  </label>
                  <label class="md:col-span-2">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldNotes') }}</span>
                    <textarea v-model="outlineDraftNotes" rows="5" class="w-full resize-none rounded-xl border border-stone-200 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.notesPlaceholder')" />
                  </label>
                </div>
              </div>

              <div class="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                <div class="flex flex-col gap-4 min-[1280px]:flex-row min-[1280px]:items-start min-[1280px]:justify-between">
                  <div>
                    <h4 class="font-semibold text-stone-900">{{ t('collectionOutline.linkedArticle') }}</h4>
                    <p class="mt-1 text-sm text-stone-500">
                      {{ outlineLinkedArticle?.title || t('collectionOutline.noLinkedArticle') }}
                    </p>
                    <p class="mt-1 text-xs leading-5 text-stone-400">{{ t('collectionOutline.linkedArticleHelp') }}</p>
                    <p class="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">{{ t('collectionOutline.multiArticleHelp') }}</p>
                  </div>
                  <div class="flex flex-wrap justify-start gap-2 min-[1280px]:justify-end">
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createArticleFromOutline">
                      {{ t('collectionOutline.createArticle') }}
                    </button>
                    <button
                      class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700 disabled:opacity-40"
                      :disabled="!store.selectedOutlineItem.entry_id"
                      @click="openLinkedOutlineArticle"
                    >
                      {{ t('collectionOutline.openArticle') }}
                    </button>
                  </div>
                </div>
                <pre v-if="outlineLinkedArticle" class="mt-4 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl bg-stone-50 p-4 text-sm leading-7 text-stone-700">{{ outlineLinkedArticle.body || t('collections.emptyArticle') }}</pre>
              </div>

              <div v-if="outlineEditing" class="flex justify-between">
                <button class="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700 hover:bg-red-100" @click="deleteSelectedOutlineItem">
                  {{ t('collectionOutline.deleteItem') }}
                </button>
              </div>
            </div>
            <div v-else class="mx-auto mt-20 max-w-xl rounded-2xl border border-dashed border-stone-300 bg-white/70 p-8 text-center text-stone-500">
              <h3 class="text-lg font-semibold text-stone-700">{{ t('collectionOutline.selectItem') }}</h3>
              <p class="mt-2 text-sm leading-6">{{ t('collectionOutline.selectItemHelp') }}</p>
            </div>
          </section>
        </template>

        <template v-else-if="viewMode === 'board'">
          <section class="flex-1 overflow-y-auto p-6" data-testid="collection-planning-board" data-tour="collections-board">
            <div class="mb-4 flex flex-col gap-3 border-b border-stone-200 pb-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h3 class="text-xl font-semibold text-stone-900">{{ t('collectionOutline.boardTitle') }}</h3>
                <p class="mt-1 text-sm text-stone-500">{{ t('collectionOutline.boardDescriptionCompact') }}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">{{ t('collectionOutline.allTypes') }}</option>
                  <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">{{ t('collectionOutline.allStatuses') }}</option>
                  <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <button
                  type="button"
                  class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                  @click="createOutlineItem('chapter')"
                >
                  {{ t('collectionOutline.newChapter') }}
                </button>
              </div>
            </div>

            <div v-if="outlineActionError || store.error" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ outlineActionError || store.error }}
            </div>
            <div v-if="store.outlineLoading" class="rounded-2xl bg-white/70 p-6 text-center text-sm text-stone-400">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!store.outline.length" class="rounded-3xl border border-dashed border-stone-300 bg-white/70 p-10 text-center">
              <div class="text-lg font-semibold text-stone-700">{{ t('collectionOutline.emptyTitle') }}</div>
              <p class="mt-2 text-sm text-stone-500">{{ t('collectionOutline.emptyStructureHint') }}</p>
              <button class="mt-5 rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="createOutlineItem('chapter')">
                {{ t('collectionOutline.newChapter') }}
              </button>
            </div>
            <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
              <section
                v-for="column in outlineBoardColumns"
                :key="column.value"
                class="min-h-[420px] rounded-3xl border border-stone-200 bg-white/60 p-3"
              >
                <div class="mb-3 flex items-center justify-between gap-2">
                  <div class="font-semibold text-stone-800">{{ column.label }}</div>
                  <span :class="['rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1', outlineStatusTone(column.value)]">
                    {{ column.items.length }}
                  </span>
                </div>
                <div v-if="!column.items.length" class="rounded-2xl border border-dashed border-stone-200 p-4 text-center text-xs leading-5 text-stone-400">
                  {{ t('collectionOutline.emptyColumn') }}
                </div>
                <div v-else class="space-y-2">
                  <article
                    v-for="item in column.items"
                    :key="item.id"
                    class="cursor-pointer rounded-2xl border border-stone-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                    @click="selectOutlineItem(item.id); viewMode = 'structure'"
                  >
                    <div class="flex items-start justify-between gap-2">
                      <h4 class="line-clamp-2 text-sm font-semibold leading-5 text-stone-900">{{ item.title || t('collectionOutline.untitled') }}</h4>
                      <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-700">
                        {{ outlineTypeLabel(item.item_type) }}
                      </span>
                    </div>
                    <p class="mt-2 line-clamp-3 text-xs leading-5 text-stone-500">
                      {{ item.summary || t('collectionOutline.noSummary') }}
                    </p>
                    <div class="mt-3 flex flex-wrap gap-1.5">
                      <span v-if="item.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-700">
                        {{ t('collectionOutline.linked') }}
                      </span>
                      <span v-if="item.target_word_count" class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
                        {{ item.target_word_count }} 字
                      </span>
                      <span v-if="item.pov" class="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-500">
                        {{ item.pov }}
                      </span>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </section>
        </template>

        <template v-else-if="viewMode === 'agent'">
          <section class="relative flex min-h-0 flex-1 overflow-hidden bg-[#f5f7f6]" data-testid="collection-agent-panel" data-tour="collection-agent-panel">
            <button v-if="agentLeftPanelOpen" class="absolute inset-0 z-20 bg-black/15 xl:hidden" :aria-label="agentCopy.close" @click="agentLeftPanelOpen = false"></button>
            <aside
              data-testid="agent-left-panel"
              :class="[
                'absolute inset-y-0 left-0 z-30 h-full w-[224px] shrink-0 flex-col border-r border-stone-200 bg-white shadow-2xl xl:static xl:z-auto xl:shadow-none',
                agentLeftPanelOpen ? 'flex' : 'hidden',
              ]"
            >
              <div class="border-b border-stone-200 px-4 py-4">
                <div class="flex items-center justify-between gap-2">
                  <div>
                    <p class="text-[10px] font-semibold uppercase tracking-[0.18em] text-teal-700">Collection Agent</p>
                    <h3 class="mt-1 text-base font-semibold text-stone-900">{{ agentCopy.workspace }}</h3>
                  </div>
                  <div class="flex items-center gap-1">
                    <button class="h-8 w-8 rounded-lg bg-stone-900 text-lg leading-none text-white hover:bg-stone-700" :title="agentCopy.newSession" @click="agentCreatingSession = !agentCreatingSession">+</button>
                    <button class="h-8 w-8 rounded-lg text-lg leading-none text-stone-400 hover:bg-stone-100 hover:text-stone-700" :title="agentCopy.close" @click="agentLeftPanelOpen = false">‹</button>
                  </div>
                </div>
                <input v-model="agentSessionQuery" class="mt-3 w-full rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs outline-none focus:bg-white focus:border-teal-500" :placeholder="agentCopy.searchSessions" />
              </div>

              <div class="min-h-0 flex-1 overflow-y-auto px-2 py-3">
                <p class="px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-stone-400">{{ agentCopy.sessions }}</p>
                <div class="mt-2 space-y-1">
                  <button
                    v-for="session in filteredAgentSessions"
                    :key="session.id"
                    :class="[
                      'w-full rounded-lg px-3 py-2.5 text-left transition',
                      session.id === agentState?.active_session_id ? 'bg-teal-50 text-teal-950 ring-1 ring-teal-100' : 'text-stone-700 hover:bg-stone-100'
                    ]"
                    @click="switchAgentSession(session)"
                  >
                    <div class="flex items-center gap-2">
                      <span class="min-w-0 flex-1 truncate text-sm font-semibold">{{ session.title }}</span>
                      <span v-if="session.archived" class="text-[10px] text-stone-400">{{ agentCopy.archived }}</span>
                    </div>
                    <div class="mt-1 flex items-center gap-2 text-[10px] text-stone-400">
                      <span>{{ session.message_count }} {{ agentCopy.messages }}</span>
                      <span v-if="session.draft_count">{{ session.draft_count }} {{ agentCopy.draftsCount }}</span>
                    </div>
                  </button>
                </div>

                <div class="mt-5 border-t border-stone-100 pt-4">
                  <div class="flex items-center justify-between px-2">
                    <p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-stone-400">{{ agentCopy.currentPrompts }}</p>
                    <button class="text-[10px] text-stone-400 hover:text-stone-700 disabled:opacity-40" :disabled="Boolean(activeAgentRun)" @click="requestAgentClear">{{ agentCopy.clear }}</button>
                  </div>
                  <input v-model="agentPromptIndexQuery" class="mx-2 mt-2 w-[calc(100%_-_1rem)] rounded-lg border border-stone-200 px-2.5 py-1.5 text-[11px] outline-none" :placeholder="agentCopy.searchPrompts" />
                  <div class="mt-2 space-y-1">
                    <button
                      v-for="run in filteredAgentPromptIndex"
                      :key="run.id"
                      class="w-full rounded-lg px-3 py-2 text-left hover:bg-stone-100"
                      @click="scrollToAgentRun(run.id)"
                    >
                      <p class="line-clamp-2 text-[11px] font-medium leading-4 text-stone-700">{{ agentRunMessage(run) || agentCopy.emptyTask }}</p>
                      <p class="mt-1 truncate text-[10px] text-stone-400">{{ agentRunTaskLabel(run) }} · {{ agentRunTimeLabel(run) }}</p>
                    </button>
                  </div>
                </div>
              </div>

              <div class="border-t border-stone-200 p-3 text-[11px] text-stone-500">
                <label class="flex items-center gap-2 px-1 py-1.5"><input v-model="agentShowArchivedSessions" type="checkbox" class="h-3.5 w-3.5 rounded border-stone-300 text-teal-700" />{{ agentCopy.showArchived }}</label>
                <button class="mt-1 w-full rounded-lg px-2 py-2 text-left hover:bg-stone-100" @click="startRenamingAgentSession">{{ agentCopy.renameSession }}</button>
                <button class="mt-1 w-full rounded-lg px-2 py-2 text-left hover:bg-stone-100 disabled:opacity-40" :disabled="Boolean(activeAgentRun) || agentSessionBusy" @click="archiveActiveAgentSession">{{ agentCopy.archiveSession }}</button>
                <button class="w-full rounded-lg px-2 py-2 text-left text-red-500 hover:bg-red-50 disabled:opacity-40" :disabled="Boolean(activeAgentRun) || agentSessionBusy" @click="deleteActiveAgentSession">{{ agentCopy.deleteSession }}</button>
              </div>
            </aside>

            <main class="flex min-w-0 flex-1 flex-col bg-[#f7f8f7]">
              <header class="shrink-0 border-b border-stone-200 bg-white px-4 py-3 sm:px-5">
                <div class="flex items-center gap-3">
                  <button
                    data-testid="agent-left-toggle"
                    :class="['rounded-lg border px-2.5 py-1.5 text-xs font-semibold', agentLeftPanelOpen ? 'border-teal-200 bg-teal-50 text-teal-800' : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50']"
                    :title="agentCopy.sessionsHelp"
                    @click="toggleAgentLeftPanel"
                  >{{ agentCopy.sessionsToggle }}</button>
                  <div class="min-w-0 flex-1">
                    <select class="w-full max-w-xs truncate bg-transparent text-sm font-semibold text-stone-900 outline-none xl:hidden" :value="agentState?.active_session_id || ''" @change="switchAgentSessionById">
                      <option v-for="session in (agentState?.sessions ?? []).filter((item) => !item.archived)" :key="session.id" :value="session.id">{{ session.title }}</option>
                    </select>
                    <div v-if="agentRenamingSession" class="hidden items-center gap-2 xl:flex"><input v-model="agentSessionTitleDraft" class="min-w-0 max-w-xs flex-1 rounded-md border border-teal-300 px-2 py-1 text-sm font-semibold outline-none" @keyup.enter="saveAgentSessionTitle" @keyup.esc="agentRenamingSession = false" /><button class="rounded-md bg-teal-700 px-2 py-1 text-[10px] font-semibold text-white" @click="saveAgentSessionTitle">{{ agentCopy.save }}</button></div>
                    <h3 v-else class="hidden truncate text-sm font-semibold text-stone-900 xl:block">{{ activeAgentSession?.title || agentCopy.defaultSession }}</h3>
                    <p class="mt-0.5 truncate text-[11px] text-stone-400">{{ currentAgentMode.help }}</p>
                  </div>
                  <button class="h-8 w-8 rounded-lg bg-stone-100 text-lg leading-none text-stone-600 hover:bg-stone-200 xl:hidden" :title="agentCopy.newSession" @click="agentCreatingSession = true; agentNewSessionTitle = locale === 'en' ? 'New session' : '新会话'">+</button>
                  <select v-model="agentProfileId" class="max-w-[150px] rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-[11px] outline-none" :title="agentCopy.nextProfile">
                    <option v-for="profile in agentProfileOptions" :key="profile.id" :value="profile.id">{{ profile.name }}</option>
                  </select>
                  <button
                    data-testid="agent-right-toggle"
                    :class="['rounded-lg border px-2.5 py-1.5 text-xs font-semibold', agentRightPanelOpen ? 'border-teal-200 bg-teal-50 text-teal-800' : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50']"
                    :title="agentCopy.resourcesHelp"
                    @click="toggleAgentRightPanel"
                  >{{ agentCopy.resources }}</button>
                </div>

                <div class="mt-3 flex items-center justify-between gap-3">
                  <div class="inline-flex min-w-0 rounded-lg bg-stone-100 p-1" role="tablist" aria-label="Agent mode">
                    <button
                      v-for="mode in agentModeOptions"
                      :key="mode.value"
                      :class="[
                        'rounded-md px-3 py-1.5 text-xs font-semibold transition',
                        agentMode === mode.value ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-800'
                      ]"
                      @click="changeAgentMode(mode.value)"
                    >{{ mode.label }}</button>
                  </div>
                  <div class="flex min-w-0 items-center gap-1 overflow-x-auto" data-testid="agent-quick-task-strip">
                    <button v-for="task in agentQuickTasks.slice(1)" :key="task.kind" class="shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] text-stone-500 hover:bg-stone-100 hover:text-stone-900" @click="runQuickAgentTask(task.kind)">{{ task.title }}</button>
                  </div>
                </div>
              </header>

              <div v-if="agentError" class="mx-4 mt-3 shrink-0 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{{ agentError }}</div>
              <div v-if="activeAgentRun" class="mx-4 mt-3 shrink-0 overflow-hidden rounded-lg border border-amber-200 bg-amber-50" data-testid="collection-agent-job-bar">
                <div class="flex items-center justify-between gap-3 px-3 py-2 text-xs text-amber-900">
                  <div class="min-w-0"><span class="font-semibold">{{ agentCopy.running }}</span><span class="ml-2 text-amber-700">{{ agentStageLabel(activeAgentRun) }}</span><span v-if="activeAgentRun.session_id !== agentState?.active_session_id" class="ml-2 text-amber-600">{{ agentCopy.otherSession }}</span></div>
                  <button class="shrink-0 rounded-md bg-white px-2.5 py-1 font-semibold ring-1 ring-amber-200" @click="cancelActiveAgentRun">{{ agentCopy.interrupt }}</button>
                </div>
                <div class="h-1 bg-amber-100"><div class="h-full w-2/5 animate-pulse bg-amber-500"></div></div>
              </div>

              <div class="min-h-0 flex-1 overflow-y-auto" data-testid="agent-conversation-scroll">
                <div class="mx-auto w-full max-w-4xl px-4 py-5 sm:px-6">
                  <div v-if="!agentLoading && !agentRuns.length" class="py-12 text-center">
                    <div class="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-teal-700 font-serif text-xl text-white">L</div>
                    <h4 class="mt-4 text-lg font-semibold text-stone-900">{{ agentCopy.zeroTitle }}</h4>
                    <p class="mx-auto mt-2 max-w-lg text-sm leading-6 text-stone-500">{{ agentCopy.zeroBody }}</p>
                    <div class="mt-5 flex flex-wrap justify-center gap-2">
                      <button class="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-stone-600 hover:border-teal-300" @click="agentPrompt = locale === 'en' ? 'I have only a vague idea. Give me three distinctly different novel directions, then ask one question at a time.' : '我只有一个模糊想法。请先给我三个差异明显的小说方向，再一次问我一个问题。'; changeAgentMode('discuss')">{{ agentCopy.zeroIdea }}</button>
                      <button class="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-stone-600 hover:border-teal-300" @click="agentPrompt = locale === 'en' ? 'Help me clarify what the protagonist truly wants and what blocks them.' : '请和我一起梳理主角真正想要什么，以及阻碍是什么。'; changeAgentMode('discuss')">{{ agentCopy.character }}</button>
                      <button class="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-stone-600 hover:border-teal-300" @click="agentPrompt = locale === 'en' ? 'Turn our confirmed ideas into a restrained chapter plan.' : '请把我们已经确认的想法整理成一个克制的章节规划。'; changeAgentMode('plan')">{{ agentCopy.structure }}</button>
                    </div>
                  </div>

                  <div class="space-y-5">
                    <article
                      v-for="run in agentRuns"
                      :key="run.id"
                      :id="`collection-agent-run-${run.id}`"
                      :class="['transition', agentHighlightedRunId === run.id ? 'rounded-xl ring-2 ring-amber-300 ring-offset-4' : '']"
                    >
                      <div class="ml-auto max-w-[88%] rounded-xl rounded-br-sm bg-stone-900 px-4 py-3 text-sm leading-6 text-white shadow-sm">
                        <p class="whitespace-pre-wrap">{{ agentRunMessage(run) }}</p>
                        <div class="mt-2 flex flex-wrap gap-2 text-[10px] text-stone-300"><span>{{ agentRunTaskLabel(run) }}</span><span>{{ agentRunTimeLabel(run) }}</span></div>
                      </div>
                      <div class="mt-3 max-w-[94%] rounded-xl rounded-bl-sm border border-stone-200 bg-white px-4 py-4 shadow-sm">
                        <div class="flex items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-400">
                          <span>{{ agentModeLabel(run.mode || 'discuss') }} · {{ run.model || run.profile_id }}</span>
                          <span :class="run.status === 'succeeded' ? 'text-emerald-700' : run.status === 'failed' ? 'text-red-600' : 'text-amber-700'">{{ agentStageLabel(run) }}</span>
                        </div>
                        <div v-if="agentRunAnswer(run)" class="mt-3 whitespace-pre-wrap text-sm leading-7 text-stone-700">{{ agentRunVisibleAnswer(run) }}</div>
                        <div v-else-if="!run.error" class="mt-3 text-sm text-stone-400">{{ agentCopy.waiting }}</div>
                        <div v-if="run.error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">{{ run.error }}</div>
                        <div v-if="agentRunConflicts(run).length" class="mt-4 space-y-2"><p class="text-[10px] font-semibold uppercase tracking-[0.14em] text-rose-700">{{ agentCopy.canonConflict }}</p><article v-for="conflict in agentRunConflicts(run)" :key="`${run.id}:${conflict.title}`" class="rounded-lg border border-rose-200 bg-rose-50/60 p-3"><h5 class="text-xs font-semibold text-rose-950">{{ conflict.title }}</h5><div class="mt-2 grid gap-2 text-[11px] leading-5 sm:grid-cols-2"><p class="rounded-md bg-white/80 p-2 text-stone-600"><span class="block text-[10px] font-semibold text-stone-400">{{ agentCopy.existingCanon }}</span>{{ conflict.existing || (locale === 'en' ? 'Not recorded' : '未记录') }}</p><p class="rounded-md bg-white/80 p-2 text-stone-600"><span class="block text-[10px] font-semibold text-stone-400">{{ agentCopy.proposedCanon }}</span>{{ conflict.proposed || (locale === 'en' ? 'Not recorded' : '未记录') }}</p></div><p v-if="conflict.reason" class="mt-2 text-[10px] leading-5 text-rose-700">{{ conflict.reason }}</p></article></div>
                        <div class="mt-3 flex flex-wrap gap-2">
                          <button v-if="agentRunCanCollapse(run)" class="rounded-md bg-stone-100 px-2.5 py-1.5 text-[11px] font-semibold text-stone-600" @click="toggleAgentRunCollapsed(run)">{{ agentCollapsedRunIds.includes(run.id) ? agentCopy.expandAnswer : agentCopy.collapseAnswer }}</button>
                          <button v-if="run.draft_id && (agentState?.drafts ?? []).some((draft) => draft.id === run.draft_id)" class="rounded-md bg-teal-50 px-2.5 py-1.5 text-[11px] font-semibold text-teal-800" @click="selectAgentDraftById(run.draft_id)">{{ agentCopy.openDraft }}</button>
                        </div>
                        <div v-if="run.actions.length" class="mt-4 border-t border-stone-100 pt-3">
                          <p class="text-[10px] font-semibold uppercase tracking-[0.14em] text-stone-400">{{ agentCopy.authorDecision }}</p>
                          <div class="mt-2 space-y-2">
                            <div v-for="action in run.actions" :key="action.id" class="flex items-start justify-between gap-3 rounded-lg bg-stone-50 px-3 py-2.5">
                              <div class="min-w-0"><p class="text-xs font-semibold text-stone-800">{{ action.title }}</p><p class="mt-1 line-clamp-2 text-[11px] leading-5 text-stone-500">{{ action.summary || action.reason }}</p></div>
                              <div v-if="['pending', 'deferred'].includes(action.status)" class="flex shrink-0 gap-1.5"><button class="rounded-md bg-stone-900 px-2.5 py-1 text-[11px] font-semibold text-white" @click="applyAgentAction(action)">{{ agentCopy.apply }}</button><button v-if="action.status === 'pending'" class="rounded-md bg-white px-2.5 py-1 text-[11px] text-stone-500 ring-1 ring-stone-200" @click="deferAgentAction(action)">{{ agentCopy.defer }}</button><button class="rounded-md bg-white px-2.5 py-1 text-[11px] text-stone-500 ring-1 ring-stone-200" @click="rejectAgentAction(action)">{{ agentCopy.reject }}</button></div>
                              <span v-else :class="['shrink-0 rounded-md px-2 py-1 text-[10px]', agentActionStatusTone(action.status)]">{{ agentActionStatusLabel(action.status) }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>
              </div>

              <footer class="shrink-0 border-t border-stone-200 bg-white px-4 py-3 sm:px-5">
                <div class="mx-auto max-w-4xl">
                  <div v-if="pendingQuickTask" class="mb-3 flex items-start justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
                    <div class="min-w-0"><p class="text-xs font-semibold text-amber-950">{{ agentCopy.prepare }}：{{ pendingQuickTask.title }}</p><p class="mt-1 line-clamp-2 text-[11px] leading-5 text-amber-700">{{ agentCopy.uses }} {{ selectedAgentProfileName }}。</p></div>
                    <div class="flex shrink-0 gap-1.5"><button class="rounded-md bg-amber-900 px-2.5 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40" :disabled="agentRunning || Boolean(activeAgentRun)" @click="confirmQuickAgentTask">{{ agentCopy.confirm }}</button><button class="rounded-md bg-white px-2.5 py-1.5 text-[11px] text-amber-800 ring-1 ring-amber-200" @click="cancelQuickAgentTask">{{ agentCopy.cancel }}</button></div>
                  </div>

                  <details v-if="agentMode === 'draft'" class="mb-3 rounded-lg border border-teal-200 bg-teal-50/60 px-3 py-2" open>
                    <summary class="cursor-pointer text-xs font-semibold text-teal-950">{{ agentCopy.sceneBrief }} <span class="ml-2 font-normal text-teal-700">{{ agentCopy.sceneBriefHelp }}</span></summary>
                    <div class="mt-3 grid gap-2 sm:grid-cols-2">
                      <input v-model="agentDraftBrief.target_scene" class="rounded-lg border border-teal-200 bg-white px-3 py-2 text-xs outline-none" :placeholder="agentCopy.targetScene" />
                      <div class="grid grid-cols-3 gap-2"><input v-model="agentDraftBrief.pov" class="rounded-lg border border-teal-200 bg-white px-2 py-2 text-xs outline-none" :placeholder="agentCopy.pov" /><input v-model="agentDraftBrief.tense" class="rounded-lg border border-teal-200 bg-white px-2 py-2 text-xs outline-none" :placeholder="agentCopy.tense" /><input v-model.number="agentDraftBrief.target_length" type="number" min="100" max="20000" class="rounded-lg border border-teal-200 bg-white px-2 py-2 text-xs outline-none" :placeholder="agentCopy.length" /></div>
                      <textarea v-model="agentDraftMustHappenText" rows="2" class="resize-none rounded-lg border border-teal-200 bg-white px-3 py-2 text-xs outline-none" :placeholder="agentCopy.must" />
                      <textarea v-model="agentDraftAvoidText" rows="2" class="resize-none rounded-lg border border-teal-200 bg-white px-3 py-2 text-xs outline-none" :placeholder="agentCopy.avoid" />
                    </div>
                  </details>

                  <div v-if="selectedAgentRefs.length" class="mb-2 flex flex-wrap gap-1.5">
                    <button v-for="ref in selectedAgentRefs" :key="`${ref.kind}:${ref.ref_id}`" class="rounded-md bg-sky-50 px-2 py-1 text-[11px] text-sky-800 ring-1 ring-sky-100" @click="removeAgentReference(ref)">{{ agentReferenceKindLabel(ref.kind) }} · {{ ref.name }} ×</button>
                  </div>

                  <div class="relative rounded-xl border border-stone-300 bg-white shadow-sm focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100">
                    <div v-if="agentReferencePickerOpen" class="absolute bottom-full left-0 z-40 mb-2 w-full rounded-xl border border-stone-200 bg-white p-3 shadow-2xl">
                      <div class="flex items-center gap-2"><input v-model="agentReferenceQuery" class="min-w-0 flex-1 rounded-lg border border-stone-200 px-3 py-2 text-xs outline-none" :placeholder="agentCopy.searchReferences" @input="searchAgentReferences" /><button class="rounded-md px-2 py-1.5 text-xs text-stone-500 hover:bg-stone-100" @click="clearAgentReferenceSearch">{{ agentCopy.clear }}</button><button class="rounded-md px-2 py-1.5 text-xs text-stone-500 hover:bg-stone-100" @click="closeAgentReferencePicker">{{ agentCopy.collapse }}</button></div>
                      <div class="mt-2 max-h-52 overflow-y-auto"><p v-if="agentSearchLoading" class="p-3 text-center text-xs text-stone-400">{{ agentCopy.searching }}</p><p v-else-if="!agentReferenceResults.length" class="p-3 text-center text-xs text-stone-400">{{ agentCopy.noReferences }}</p><template v-else><button v-for="ref in agentReferenceResults" :key="`${ref.kind}:${ref.ref_id}`" class="flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left hover:bg-stone-50" @click="addAgentReference(ref)"><span class="shrink-0 rounded bg-stone-100 px-1.5 py-0.5 text-[10px] text-stone-500">{{ agentReferenceKindLabel(ref.kind) }}</span><span class="min-w-0"><span class="block truncate text-xs font-semibold text-stone-800">{{ ref.name }}</span><span class="mt-0.5 block truncate text-[11px] text-stone-400">{{ ref.body_preview || (locale === 'en' ? 'No preview' : '无预览') }}</span></span></button></template></div>
                    </div>

                    <div v-if="agentSlashMenuOpen" class="absolute bottom-full left-0 z-40 mb-2 w-full rounded-xl border border-stone-200 bg-white p-2 shadow-2xl" data-testid="agent-slash-menu">
                      <button v-for="(command, index) in filteredAgentSlashCommands" :key="command.command" :class="['flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left', index === agentSlashSelectedIndex ? 'bg-stone-900 text-white' : 'text-stone-700 hover:bg-stone-50']" @mousedown.prevent="selectAgentSlashCommand(command)"><span class="font-mono text-[11px]">/{{ command.command }}</span><span class="min-w-0"><span class="block text-xs font-semibold">{{ command.title }}</span><span :class="['block truncate text-[11px]', index === agentSlashSelectedIndex ? 'text-stone-300' : 'text-stone-400']">{{ command.subtitle }}</span></span></button>
                    </div>

                    <textarea v-model="agentPrompt" rows="3" class="block w-full resize-none rounded-xl border-0 bg-transparent px-3.5 py-3 text-sm leading-6 outline-none" :placeholder="agentMode === 'draft' ? agentCopy.draftPlaceholder : agentCopy.discussPlaceholder" @keydown="handleAgentPromptKeydown" @input="handleAgentPromptInput" />
                    <div class="flex items-center justify-between border-t border-stone-100 px-2.5 py-2">
                      <div class="flex items-center gap-1"><button class="rounded-md px-2 py-1.5 text-xs text-stone-500 hover:bg-stone-100" :title="agentCopy.addReference" @click="openAgentReferencePicker()">@ {{ agentCopy.addReference }}</button><label class="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] text-stone-500 hover:bg-stone-100"><input v-model="agentRequestWebContext" type="checkbox" class="h-3.5 w-3.5 rounded border-stone-300 text-teal-700" />{{ agentCopy.web }}</label></div>
                      <button class="rounded-lg bg-teal-700 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-40" :disabled="agentRunning || Boolean(activeAgentRun) || !agentPrompt.trim()" @click="runAgentPrompt()">{{ agentRunning ? agentCopy.starting : agentMode === 'draft' ? agentCopy.generate : agentCopy.send }}</button>
                    </div>
                  </div>
                </div>
              </footer>
            </main>

            <button v-if="agentRightPanelOpen" class="absolute inset-0 z-20 bg-black/15 min-[1760px]:hidden" :aria-label="agentCopy.close" @click="agentRightPanelOpen = false"></button>
            <aside
              data-testid="agent-right-panel"
              :class="[
                'absolute inset-y-0 right-0 z-30 w-[min(350px,92vw)] shrink-0 flex-col border-l border-stone-200 bg-white shadow-2xl min-[1760px]:static min-[1760px]:z-auto min-[1760px]:w-[320px] min-[1760px]:shadow-none',
                agentRightPanelOpen ? 'flex' : 'hidden',
              ]"
            >
              <div class="flex shrink-0 items-center gap-1 border-b border-stone-200 p-2">
                <button v-for="tab in agentRightTabs" :key="tab.id" :class="['flex-1 rounded-md px-2 py-2 text-xs font-semibold', agentRightTab === tab.id ? 'bg-stone-900 text-white' : 'text-stone-500 hover:bg-stone-100']" @click="setAgentRightTab(tab.id)">{{ tab.label }}</button>
                <button class="ml-1 h-8 w-8 rounded-md text-stone-400 hover:bg-stone-100" :aria-label="agentCopy.close" @click="agentRightPanelOpen = false">×</button>
              </div>

              <div class="min-h-0 flex-1 overflow-y-auto p-4">
                <template v-if="agentRightTab === 'context'">
                  <section>
                    <div class="flex items-start justify-between gap-3"><div><h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.readTitle }}</h4><p class="mt-1 text-[11px] leading-5 text-stone-500">{{ agentCopy.readHelp }}</p></div><button class="shrink-0 rounded-md bg-stone-100 px-2 py-1 text-[10px] text-stone-500" @click="loadAgentState(agentState?.active_session_id)">{{ agentCopy.refresh }}</button></div>
                    <label class="mt-4 flex items-center justify-between gap-3 rounded-lg border border-stone-200 px-3 py-2"><span><span class="block text-[11px] font-semibold text-stone-700">{{ agentCopy.collectionDefault }}</span><span class="mt-0.5 block text-[10px] text-stone-400">{{ agentCopy.nextOverride }}</span></span><select v-model="agentDefaultProfileId" class="max-w-[140px] rounded-md border border-stone-200 px-2 py-1.5 text-[10px] outline-none" @change="saveAgentSettings"><option v-for="profile in agentProfileOptions" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select></label>
                    <dl class="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-stone-200 bg-stone-200 text-xs">
                      <div class="bg-white p-3"><dt class="text-[10px] text-stone-400">{{ agentCopy.projectBible }}</dt><dd class="mt-1 font-semibold text-stone-800">{{ agentCopy.included }}</dd></div>
                      <div class="bg-white p-3"><dt class="text-[10px] text-stone-400">{{ agentCopy.recentChat }}</dt><dd class="mt-1 font-semibold text-stone-800">{{ agentCopy.maxSix }}</dd></div>
                      <div class="bg-white p-3"><dt class="text-[10px] text-stone-400">{{ agentCopy.explicitRefs }}</dt><dd class="mt-1 font-semibold text-stone-800">{{ selectedAgentRefs.length }}</dd></div>
                      <div class="bg-white p-3"><dt class="text-[10px] text-stone-400">{{ agentCopy.wholeBook }}</dt><dd class="mt-1 font-semibold text-stone-800">{{ agentCopy.notRead }}</dd></div>
                    </dl>
                    <p v-if="latestAgentContextLabel" class="mt-3 rounded-lg bg-stone-50 px-3 py-2 text-[10px] leading-5 text-stone-500">{{ latestAgentContextLabel }}</p>
                    <div v-if="activeAgentSession?.summary" class="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-3"><div class="flex items-center justify-between"><span class="text-xs font-semibold text-sky-900">{{ agentCopy.sessionSummary }}</span><button class="text-[10px] text-sky-700" @click="compactActiveAgentSession">{{ agentCopy.rebuildSummary }}</button></div><p class="mt-2 whitespace-pre-wrap text-[11px] leading-5 text-sky-800">{{ activeAgentSession.summary }}</p><p class="mt-2 text-[10px] text-sky-600">{{ agentCopy.sessionSummaryHelp }}</p></div>
                    <button class="mt-4 w-full rounded-lg border border-dashed border-stone-300 px-3 py-2.5 text-xs font-semibold text-stone-600 hover:border-teal-400 hover:text-teal-800" @click="openAgentReferencePicker()">+ {{ agentCopy.addRunRef }}</button>
                  </section>

                  <section class="mt-6 border-t border-stone-100 pt-5">
                    <div class="flex items-center justify-between"><h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.proposals }}</h4><span class="rounded-md bg-amber-50 px-2 py-1 text-[10px] font-semibold text-amber-800">{{ pendingAgentActions.length }}</span></div>
                    <p v-if="!pendingAgentActions.length" class="mt-3 text-xs leading-5 text-stone-400">{{ agentCopy.noProposals }}</p>
                    <div v-else class="mt-3 space-y-2"><article v-for="action in pendingAgentActions" :key="action.id" class="rounded-lg border border-stone-200 p-3"><p class="text-[10px] text-stone-400">{{ agentActionTypeLabel(action.action_type) }}<span v-if="action.status === 'deferred'"> · {{ agentCopy.deferred }}</span></p><h5 class="mt-1 text-xs font-semibold text-stone-800">{{ action.title }}</h5><p class="mt-1 line-clamp-3 text-[11px] leading-5 text-stone-500">{{ action.summary || action.reason }}</p><details class="mt-2"><summary class="cursor-pointer text-[10px] text-stone-400">{{ agentCopy.viewChange }}</summary><pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-stone-50 p-2 text-[10px] leading-4 text-stone-600">{{ formatAgentPreview(action.preview) }}</pre></details><div class="mt-3 flex gap-2"><button class="rounded-md bg-stone-900 px-2.5 py-1.5 text-[11px] font-semibold text-white" @click="applyAgentAction(action)">{{ agentCopy.apply }}</button><button v-if="action.status === 'pending'" class="rounded-md bg-stone-100 px-2.5 py-1.5 text-[11px] text-stone-600" @click="deferAgentAction(action)">{{ agentCopy.defer }}</button><button class="rounded-md bg-stone-100 px-2.5 py-1.5 text-[11px] text-stone-600" @click="rejectAgentAction(action)">{{ agentCopy.reject }}</button></div></article></div>
                  </section>
                </template>

                <template v-else-if="agentRightTab === 'drafts'">
                  <div class="flex items-start justify-between gap-3"><div><h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.draftLibrary }}</h4><p class="mt-1 text-[11px] leading-5 text-stone-500">{{ agentCopy.draftLibraryHelp }}</p></div><div v-if="unappliedAgentDrafts.length" class="flex shrink-0 gap-2"><button v-if="agentDraftSelectedIds.length" class="text-[10px] text-red-500 hover:text-red-700" @click="deleteSelectedAgentDrafts(false)">{{ agentCopy.deleteSelected }}</button><button class="text-[10px] text-red-500 hover:text-red-700" @click="deleteSelectedAgentDrafts(true)">{{ agentCopy.clearUnapplied }}</button></div></div>
                  <div v-if="!currentAgentDrafts.length" class="mt-5 rounded-lg border border-dashed border-stone-300 p-5 text-center text-xs leading-5 text-stone-400">{{ agentCopy.emptyDrafts }}</div>
                  <div v-else class="mt-4 space-y-2">
                    <div v-for="draft in currentAgentDrafts" :key="draft.id" class="flex items-start gap-2"><input v-if="draft.status === 'draft'" type="checkbox" class="mt-3.5 h-3.5 w-3.5 rounded border-stone-300 text-teal-700" :checked="agentDraftSelectedIds.includes(draft.id)" :aria-label="`${agentCopy.draftsTab} ${draft.title}`" @change="toggleAgentDraftSelection(draft.id)" /><span v-else class="w-3.5"></span><button :class="['min-w-0 flex-1 rounded-lg border p-3 text-left', selectedAgentDraftId === draft.id ? 'border-teal-300 bg-teal-50' : 'border-stone-200 hover:bg-stone-50']" @click="selectAgentDraft(draft)"><div class="flex items-center justify-between gap-2"><span class="truncate text-xs font-semibold text-stone-800">{{ draft.title }}</span><span :class="draft.status === 'applied' ? 'text-emerald-700' : 'text-stone-400'" class="text-[10px]">{{ draft.status === 'applied' ? agentCopy.applied : draft.variant_label || agentCopy.primaryDraft }}</span></div><p class="mt-1 line-clamp-2 text-[11px] leading-5 text-stone-500">{{ draft.content }}</p></button></div>
                  </div>

                  <section v-if="selectedAgentDraft" class="mt-5 border-t border-stone-100 pt-4">
                    <input v-model="agentDraftTitle" :disabled="selectedAgentDraft.status === 'applied'" class="w-full border-0 border-b border-stone-200 px-0 py-2 text-sm font-semibold text-stone-900 outline-none disabled:bg-white" />
                    <textarea v-model="agentDraftContent" :disabled="selectedAgentDraft.status === 'applied'" rows="14" class="mt-3 w-full resize-y rounded-lg border border-stone-200 px-3 py-3 text-xs leading-6 text-stone-700 outline-none focus:border-teal-400 disabled:bg-stone-50" />
                    <div v-if="selectedAgentDraft.status === 'draft'" class="mt-3 grid grid-cols-2 gap-2"><button class="rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40" :disabled="agentDraftSaving" @click="saveSelectedAgentDraft">{{ agentDraftSaving ? agentCopy.saving : agentCopy.saveChanges }}</button><button class="rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white" @click="openAgentDraftApply(selectedAgentDraft)">{{ agentCopy.writeArticle }}</button><button class="rounded-lg bg-stone-100 px-3 py-2 text-xs text-stone-600" @click="requestAgentDraftVariant(selectedAgentDraft)">{{ agentCopy.variant }}</button><button class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600" @click="deleteSelectedAgentDrafts(false)">{{ agentCopy.deleteDraft }}</button></div>
                    <p v-else class="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">{{ agentCopy.appliedHelp }}</p>
                  </section>
                </template>

                <template v-else>
                  <section>
                    <div class="flex items-start justify-between gap-3"><div><h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.portrait }}</h4><p class="mt-1 text-[11px] leading-5 text-stone-500">{{ agentCopy.portraitHelp }}</p></div><button class="shrink-0 text-[10px] text-stone-500 hover:text-stone-800" @click="loadAgentPortraitHistory">{{ agentCopy.history }}</button></div>
                    <input v-model="agentPortraitTagsText" class="mt-3 w-full rounded-lg border border-stone-200 px-3 py-2 text-xs outline-none" :placeholder="agentCopy.portraitTags" />
                    <textarea v-model="agentPortraitSummary" rows="4" class="mt-2 w-full resize-y rounded-lg border border-stone-200 px-3 py-2 text-xs leading-5 outline-none" :placeholder="agentCopy.portraitSummary" />
                    <div class="mt-2 flex items-center justify-between gap-2"><span class="text-[10px] text-stone-400">{{ agentState?.author_portrait?.completed_style_cycles || 0 }} {{ agentCopy.cycles }}</span><button class="rounded-md bg-stone-900 px-2.5 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40" :disabled="agentPortraitSaving" @click="saveAgentPortrait">{{ agentCopy.savePortrait }}</button></div>
                    <div v-if="agentState?.author_portrait?.reminder_due" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3"><p class="text-[11px] leading-5 text-amber-800">{{ agentCopy.portraitReminder }}</p><button class="mt-2 rounded-md bg-amber-900 px-2.5 py-1.5 text-[11px] font-semibold text-white" @click="requestAuthorPortraitProposal">{{ agentCopy.proposePortrait }}</button></div>
                  </section>

                  <section class="mt-6 border-t border-stone-100 pt-5">
                    <h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.styleCycles }}</h4>
                    <p class="mt-1 text-[11px] leading-5 text-stone-500">{{ agentCopy.styleCyclesHelp }}</p>
                    <div v-if="activeStyleSample" class="mt-3 rounded-lg bg-sky-50 p-3"><p class="text-xs font-semibold text-sky-900">{{ agentCopy.inProgress }}：{{ allArticles.find((item) => item.id === activeStyleSample?.entry_id)?.title || agentCopy.article }}</p><button class="mt-2 rounded-md bg-sky-800 px-2.5 py-1.5 text-[11px] font-semibold text-white" @click="completeAgentStyleCycle">{{ agentCopy.completeChapter }}</button></div>
                    <div v-else class="mt-3 flex gap-2"><select v-model="agentStyleEntryId" class="min-w-0 flex-1 rounded-lg border border-stone-200 px-2 py-2 text-xs outline-none"><option value="">{{ agentCopy.chooseArticle }}</option><option v-for="article in store.articles" :key="article.id" :value="article.id">{{ article.title }}</option></select><button class="shrink-0 rounded-lg bg-sky-800 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40" :disabled="!agentStyleEntryId" @click="startAgentStyleCycle">{{ agentCopy.start }}</button></div>
                  </section>

                  <section class="mt-6 border-t border-stone-100 pt-5">
                    <div class="flex items-center justify-between"><div><h4 class="text-sm font-semibold text-stone-900">{{ agentCopy.projectBible }}</h4><p class="mt-1 text-[11px] text-stone-500">{{ locale === 'en' ? 'Author-confirmed canon shared by every session in this collection.' : '当前作品集所有会话共享的 canon。' }}</p></div><button class="rounded-md bg-teal-700 px-2.5 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40" :disabled="agentMemorySaving" @click="saveAgentMemory">{{ agentMemorySaving ? agentCopy.saving : agentCopy.save }}</button></div>
                    <div v-if="agentState" class="mt-3 space-y-2"><details v-for="section in agentState.memory.sections" :key="section.id" class="rounded-lg border border-stone-200 bg-white px-3 py-2"><summary class="cursor-pointer text-xs font-semibold text-stone-700">{{ agentMemorySectionCopy(section).title }} <span v-if="agentMemoryDraft[section.id]" class="ml-1 text-teal-600">·</span></summary><p class="mt-2 text-[10px] leading-4 text-stone-400">{{ agentMemorySectionCopy(section).help }}</p><textarea v-model="agentMemoryDraft[section.id]" rows="4" class="mt-2 w-full resize-y rounded-md border border-stone-200 px-2.5 py-2 text-[11px] leading-5 outline-none focus:border-teal-400" /></details></div>
                    <p class="mt-3 text-[10px] leading-5 text-stone-400">{{ agentCopy.memoryRule }}</p>
                  </section>
                </template>
              </div>
            </aside>

            <div v-if="agentCreatingSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4" @click.self="agentCreatingSession = false">
              <div class="w-full max-w-sm rounded-xl bg-white p-5 shadow-2xl"><div class="flex items-center justify-between"><h3 class="text-base font-semibold text-stone-900">{{ agentCopy.newSessionTitle }}</h3><button class="h-8 w-8 rounded-md text-stone-400 hover:bg-stone-100" :aria-label="agentCopy.close" @click="agentCreatingSession = false">×</button></div><p class="mt-2 text-xs leading-5 text-stone-500">{{ agentCopy.newSessionHelp }}</p><input v-model="agentNewSessionTitle" autofocus class="mt-4 w-full rounded-lg border border-stone-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500" :placeholder="agentCopy.sessionExample" @keyup.enter="createAgentSession" /><div class="mt-4 flex justify-end gap-2"><button class="rounded-lg bg-stone-100 px-3 py-2 text-xs text-stone-600" @click="agentCreatingSession = false">{{ agentCopy.cancel }}</button><button class="rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40" :disabled="agentSessionBusy" @click="createAgentSession">{{ agentSessionBusy ? agentCopy.creating : agentCopy.create }}</button></div></div>
            </div>

            <div v-if="agentDraftApplyOpen && selectedAgentDraft" class="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4" @click.self="agentDraftApplyOpen = false">
              <div class="w-full max-w-lg rounded-xl bg-white p-5 shadow-2xl">
                <div class="flex items-start justify-between gap-3"><div><h3 class="text-base font-semibold text-stone-900">{{ agentCopy.draftApplyTitle }}</h3><p class="mt-1 text-xs leading-5 text-stone-500">{{ agentCopy.draftApplyHelp }}</p></div><button class="h-8 w-8 rounded-md text-stone-400 hover:bg-stone-100" :aria-label="agentCopy.close" @click="agentDraftApplyOpen = false">×</button></div>
                <div class="mt-5 inline-flex rounded-lg bg-stone-100 p-1"><button v-for="option in agentDraftApplyOptions" :key="option.id" :class="['rounded-md px-3 py-1.5 text-xs font-semibold', agentDraftApplyOperation === option.id ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500']" @click="setAgentDraftApplyOperation(option.id)">{{ option.label }}</button></div>
                <label v-if="agentDraftApplyOperation === 'create_article'" class="mt-4 block text-xs font-semibold text-stone-600">{{ agentCopy.articleTitle }}<input v-model="agentDraftArticleTitle" class="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2.5 text-sm outline-none" /></label>
                <label v-else class="mt-4 block text-xs font-semibold text-stone-600">{{ agentCopy.targetArticle }}<select v-model="agentDraftTargetEntryId" class="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2.5 text-sm outline-none"><option v-for="article in store.articles" :key="article.id" :value="article.id">{{ article.title }}</option></select></label>
                <label v-if="agentDraftApplyOperation === 'replace_selection'" class="mt-4 block text-xs font-semibold text-stone-600">{{ agentCopy.uniqueSelection }}<textarea v-model="agentDraftSelectionText" rows="4" class="mt-1 w-full resize-y rounded-lg border border-stone-200 px-3 py-2 text-xs leading-5 outline-none" /></label>
                <div class="mt-4 rounded-lg bg-stone-50 p-3"><p class="text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-400">{{ agentCopy.writePreview }}</p><p class="mt-2 line-clamp-6 whitespace-pre-wrap text-xs leading-5 text-stone-600">{{ agentDraftContent }}</p></div>
                <div class="mt-5 flex justify-end gap-2"><button class="rounded-lg bg-stone-100 px-4 py-2 text-xs text-stone-600" @click="agentDraftApplyOpen = false">{{ agentCopy.cancel }}</button><button class="rounded-lg bg-teal-700 px-4 py-2 text-xs font-semibold text-white disabled:opacity-40" :disabled="agentDraftApplying" @click="applySelectedAgentDraft">{{ agentDraftApplying ? agentCopy.applying : agentCopy.confirmWrite }}</button></div>
              </div>
            </div>

            <div v-if="agentPortraitHistoryOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4" @click.self="agentPortraitHistoryOpen = false">
              <div class="w-full max-w-lg rounded-xl bg-white p-5 shadow-2xl"><div class="flex items-center justify-between"><h3 class="text-base font-semibold text-stone-900">{{ agentCopy.portraitVersions }}</h3><button class="h-8 w-8 rounded-md text-stone-400 hover:bg-stone-100" :aria-label="agentCopy.close" @click="agentPortraitHistoryOpen = false">×</button></div><p v-if="!agentPortraitVersions.length" class="mt-5 text-center text-xs text-stone-400">{{ agentCopy.noPortraitVersions }}</p><div v-else class="mt-4 max-h-[60vh] space-y-2 overflow-y-auto"><article v-for="version in agentPortraitVersions" :key="version.id" class="rounded-lg border border-stone-200 p-3"><div class="flex items-start justify-between gap-3"><div><p class="text-xs font-semibold text-stone-800">{{ version.tags.join(' · ') || agentCopy.noTags }}</p><p class="mt-1 line-clamp-3 text-[11px] leading-5 text-stone-500">{{ version.summary || agentCopy.emptyPortrait }}</p><p class="mt-1 text-[10px] text-stone-400">{{ version.reason }} · {{ version.created_at }}</p></div><button class="shrink-0 rounded-md bg-stone-900 px-2.5 py-1.5 text-[11px] font-semibold text-white" @click="restoreAgentPortraitVersion(version.id)">{{ agentCopy.restore }}</button></div></article></div></div>
            </div>
          </section>
        </template>

        <template v-else-if="viewMode === 'export'">
          <section class="flex-1 overflow-y-auto p-8" data-tour="collections-export-panel">
            <div class="mx-auto max-w-4xl space-y-5">
              <div class="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Export</p>
                <h3 class="mt-1 text-2xl font-semibold text-stone-900">{{ t('collectionOutline.exportTitle') }}</h3>
                <p class="mt-2 text-sm leading-6 text-stone-500">
                  {{ hasLinkedStructure ? t('collectionOutline.exportStructureMode') : t('collectionOutline.exportFallbackMode') }}
                </p>
                <div v-if="unplanned.length && hasLinkedStructure" class="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
                  {{ t('collectionOutline.unplannedExportWarning', { count: unplanned.length }) }}
                </div>
                <div class="mt-6 flex flex-wrap gap-3">
                  <button
                    class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('md')"
                  >
                    {{ store.exportingFormat === 'md' ? '...' : 'Markdown' }}
                  </button>
                  <button
                    class="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm ring-1 ring-stone-200 disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('txt')"
                  >
                    {{ store.exportingFormat === 'txt' ? '...' : 'TXT' }}
                  </button>
                  <button
                    class="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm ring-1 ring-stone-200 disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('docx')"
                  >
                    {{ store.exportingFormat === 'docx' ? '...' : 'DOCX' }}
                  </button>
                </div>
              </div>

              <div class="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
                <h4 class="font-semibold text-stone-900">{{ t('collectionOutline.planningExportTitle') }}</h4>
                <p class="mt-2 text-sm leading-6 text-stone-500">{{ t('collectionOutline.planningExportHelp') }}</p>
                <div class="mt-4 flex flex-wrap gap-2">
                  <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                    <option value="all">{{ t('collectionOutline.allTypes') }}</option>
                    <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                    <option value="all">{{ t('collectionOutline.allStatuses') }}</option>
                    <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <label class="flex items-center gap-2 rounded-xl bg-stone-50 px-3 py-2 text-xs text-stone-600">
                    <input v-model="outlineFilterUnlinkedOnly" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-indigo-600" />
                    {{ t('collectionOutline.unlinkedOnly') }}
                  </label>
                  <button
                    type="button"
                    class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700 disabled:opacity-40"
                    :disabled="outlineExporting"
                    @click="exportOutlineMarkdown"
                  >
                    {{ outlineExporting ? t('collectionOutline.exporting') : t('collectionOutline.exportPlanningMarkdown') }}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </template>
      </div>
    </main>

    <ContextMenu
      :open="deleteContextMenuOpen"
      :x="deleteContextMenuX"
      :y="deleteContextMenuY"
      :items="[{ key: 'delete', label: t('common.delete'), danger: true }]"
      @close="closeDeleteContextMenu"
      @select="handleDeleteContextMenuSelect"
    />

    <div v-if="createDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="w-full max-w-[480px] rounded-3xl bg-white p-6 shadow-2xl">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-xl font-semibold">{{ t('collections.createTitle') }}</h3>
          <button class="rounded-lg px-2 py-1 text-sm font-semibold text-stone-400 hover:bg-stone-100 hover:text-stone-700" @click="createDialogOpen = false">×</button>
        </div>
        <input
          v-model="newTitle"
          class="mt-5 w-full rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300"
          :placeholder="t('collections.titlePlaceholder')"
        />
        <select v-model="newProjectType" class="mt-3 w-full rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300">
          <option v-for="option in projectTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <textarea
          v-model="newDescription"
          rows="4"
          class="mt-3 w-full resize-none rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300"
          :placeholder="t('collections.descriptionPlaceholder')"
        />
        <div v-if="actionError || store.error" class="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ actionError || store.error }}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm" @click="createDialogOpen = false">
            {{ t('common.cancel') }}
          </button>
          <button
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            :disabled="!newTitle.trim()"
            @click="createCollection"
          >
            {{ t('common.create') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="articlePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="flex max-h-[82vh] w-full max-w-[720px] flex-col rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-stone-200 p-6">
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="text-xl font-semibold">{{ t('collections.pickArticles') }}</h3>
              <p class="mt-1 text-sm text-stone-500">{{ t('collections.pickHint') }}</p>
            </div>
            <button class="rounded-lg px-2 py-1 text-sm font-semibold text-stone-400 hover:bg-stone-100 hover:text-stone-700" @click="articlePickerOpen = false">×</button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="actionError || store.error" class="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ actionError || store.error }}
          </div>
          <div v-if="!allArticles.length" class="p-8 text-center text-stone-400">
            {{ t('collections.noArticlesAvailable') }}
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="article in allArticles"
              :key="article.id"
              :class="[
                'w-full rounded-2xl border p-4 text-left transition-all',
                selectedArticleIds.includes(article.id)
                  ? 'border-amber-400 bg-amber-50'
                  : 'border-stone-200 hover:border-stone-300',
                currentArticleIds.has(article.id) ? 'cursor-not-allowed opacity-45' : ''
              ]"
              :disabled="currentArticleIds.has(article.id)"
              @click="togglePickArticle(article.id)"
            >
              <div class="flex items-start gap-3">
                <input
                  type="checkbox"
                  class="mt-1"
                  :checked="selectedArticleIds.includes(article.id) || currentArticleIds.has(article.id)"
                  :disabled="currentArticleIds.has(article.id)"
                  readonly
                />
                <div class="min-w-0 flex-1">
                  <div class="font-semibold">{{ article.title || t('articles.untitled') }}</div>
                  <p class="mt-1 line-clamp-2 text-sm text-stone-500">
                    {{ articlePreview(article.body) }}
                  </p>
                  <div v-if="currentArticleIds.has(article.id)" class="mt-2 text-xs text-amber-700">
                    {{ t('collections.alreadyInCollection') }}
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between border-t border-stone-200 p-5">
          <span class="text-sm text-stone-500">
            {{ t('collections.selectedCount', { count: selectedArticleIds.length }) }}
          </span>
          <div class="flex gap-3">
            <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm" @click="articlePickerOpen = false">
              {{ t('common.cancel') }}
            </button>
            <button
              class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              :disabled="!selectedArticleIds.length"
              @click="addSelectedArticles"
            >
              {{ t('collections.addSelected') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="agentClearDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
        <h3 class="text-xl font-semibold text-stone-900">{{ agentCopy.clearTitle }}</h3>
        <p class="mt-3 text-sm leading-6 text-stone-600">
          {{ agentCopy.clearHelp }}
        </p>
        <p class="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
          {{ agentCopy.clearMemoryHelp }}
        </p>
        <div v-if="agentError" class="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ agentError }}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm text-stone-700" :disabled="agentClearing" @click="agentClearDialogOpen = false">
            {{ agentCopy.cancel }}
          </button>
          <button
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            :disabled="agentClearing || Boolean(activeAgentRun)"
            @click="clearAgentConversation"
          >
            {{ agentClearing ? agentCopy.clearing : agentCopy.confirmClear }}
          </button>
        </div>
      </div>
    </div>

    <GuidedTourOverlay
      :open="tourOpen"
      :steps="collectionTourSteps"
      :step-index="tourStepIndex"
      :previous-label="t('collectionsTour.previous')"
      :next-label="t('collectionsTour.next')"
      :skip-label="t('collectionsTour.skip')"
      :finish-label="t('collectionsTour.finish')"
      :progress-label="currentTourProgressLabel"
      @previous="previousCollectionTourStep"
      @next="nextCollectionTourStep"
      @close="closeCollectionTour"
      @finish="finishCollectionTour"
    />
  </div>
</template>
