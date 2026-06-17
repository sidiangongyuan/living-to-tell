import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAiWorkspaceStore } from './workspaceStore'

describe('AI workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('keeps task input, context, and result isolated by task for the current app session', () => {
    const workspace = useAiWorkspaceStore()

    workspace.currentTask().taskInput = '原文'
    workspace.currentTask().taskResult = '润色结果'
    workspace.currentTask().showComparison = true
    workspace.currentTask().manualContextItems = [{
      uid: 'reference:r1',
      kind: 'reference',
      ref_id: 'r1',
      title: '文脉',
      subtitle: '风格',
      body: '参考内容',
    }]

    workspace.setTaskType('expand')
    expect(workspace.currentTask().taskInput).toBe('')
    expect(workspace.currentTask().taskResult).toBe('')
    expect(workspace.currentTask().showComparison).toBe(false)
    expect(workspace.currentTask().manualContextItems).toEqual([])

    workspace.currentTask().taskResult = '扩写结果'
    workspace.setTaskType('polish')
    expect(workspace.currentTask().taskInput).toBe('原文')
    expect(workspace.currentTask().taskResult).toBe('润色结果')
    expect(workspace.currentTask().showComparison).toBe(true)
    expect(workspace.currentTask().manualContextItems[0]?.title).toBe('文脉')
  })

  it('clears only the current result unless explicitly clearing more state', () => {
    const workspace = useAiWorkspaceStore()
    workspace.currentTask().taskInput = '原文'
    workspace.currentTask().taskResult = '润色结果'
    workspace.currentTask().showComparison = true
    workspace.currentTask().notice = 'ok'

    workspace.clearCurrentResult()
    expect(workspace.currentTask().taskInput).toBe('原文')
    expect(workspace.currentTask().taskResult).toBe('')
    expect(workspace.currentTask().showComparison).toBe(false)

    workspace.clearCurrentTask()
    expect(workspace.currentTask().taskInput).toBe('')
  })
})
