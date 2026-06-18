import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cloneControls, createDefaultControls, type TaskControls } from './taskControls'

export type TaskType = 'polish' | 'rewrite' | 'expand' | 'continue' | 'style_transfer' | 'summarize' | 'outline' | 'title'
export type AiTab = 'tools' | 'chat'
export type ToolScope = 'paste' | 'article'
export type ContextKind = 'ai_card' | 'writing_note' | 'reference'

export interface ContextItem {
  uid: string
  kind: ContextKind
  ref_id: string
  title: string
  subtitle: string
  body: string
}

export interface RouteSelection {
  articleId: string
  start: number
  end: number
}

export interface AiTaskWorkspaceState {
  taskInput: string
  taskResult: string
  showComparison: boolean
  selectedCardIds: string[]
  manualContextItems: ContextItem[]
  scopeType: ToolScope
  selectedArticleId: string | null
  routeSelection: RouteSelection | null
  controls: TaskControls
  selectedPresetId: string
  error: string
  notice: string
}

const TASK_TYPES: TaskType[] = [
  'polish',
  'rewrite',
  'expand',
  'continue',
  'style_transfer',
  'summarize',
  'outline',
  'title',
]

function createTaskState(): AiTaskWorkspaceState {
  return {
    taskInput: '',
    taskResult: '',
    showComparison: false,
    selectedCardIds: [],
    manualContextItems: [],
    scopeType: 'paste',
    selectedArticleId: null,
    routeSelection: null,
    controls: createDefaultControls(),
    selectedPresetId: '',
    error: '',
    notice: '',
  }
}

function createTaskStates(): Record<TaskType, AiTaskWorkspaceState> {
  return Object.fromEntries(TASK_TYPES.map((task) => [task, createTaskState()])) as Record<TaskType, AiTaskWorkspaceState>
}

export const useAiWorkspaceStore = defineStore('ai-workspace', () => {
  const activeTab = ref<AiTab>('tools')
  const taskType = ref<TaskType>('polish')
  const tasks = ref<Record<TaskType, AiTaskWorkspaceState>>(createTaskStates())
  const chatScopeKind = ref<'global' | 'article' | 'collection'>('article')
  const chatScopeId = ref<string | null>(null)
  const chatInput = ref('')

  function currentTask(): AiTaskWorkspaceState {
    return tasks.value[taskType.value]
  }

  function ensureTask(task: TaskType): AiTaskWorkspaceState {
    if (!tasks.value[task]) {
      tasks.value[task] = createTaskState()
    }
    return tasks.value[task]
  }

  function setTaskType(task: TaskType) {
    ensureTask(task)
    taskType.value = task
  }

  function clearCurrentResult() {
    const task = currentTask()
    task.taskResult = ''
    task.showComparison = false
    task.notice = ''
  }

  function clearCurrentTask() {
    tasks.value[taskType.value] = createTaskState()
  }

  function clearAllTools() {
    tasks.value = createTaskStates()
    taskType.value = 'polish'
    chatScopeKind.value = 'article'
    chatScopeId.value = null
    chatInput.value = ''
  }

  function cloneCurrentControls(): TaskControls {
    return cloneControls(currentTask().controls)
  }

  return {
    activeTab,
    taskType,
    tasks,
    chatScopeKind,
    chatScopeId,
    chatInput,
    currentTask,
    ensureTask,
    setTaskType,
    clearCurrentResult,
    clearCurrentTask,
    clearAllTools,
    cloneCurrentControls,
  }
})
