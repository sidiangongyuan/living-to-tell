import { describe, expect, it } from 'vitest'
import type { AiCard } from '../../api/aiCards'
import { buildCardCombinationPrompt, buildCardCombinationTaskRequest, selectedCards } from './cardCombination'

function card(id: string, card_type: AiCard['card_type'], title: string): AiCard {
  return {
    id,
    card_type,
    title,
    content: `【测试】${title}`,
    tags: [],
    created_at: null,
    updated_at: null,
  }
}

describe('card combination helpers', () => {
  it('keeps only manually selected cards in context', () => {
    const style = card('style-1', 'style', '克制风格')
    const scene = card('scene-1', 'scene', '久别重逢')

    expect(selectedCards({ style, character: null, scene }).map((item) => item.id)).toEqual(['style-1', 'scene-1'])
  })

  it('builds a prompt that explains target and avoids copying source quotes', () => {
    const prompt = buildCardCombinationPrompt({
      target: 'scene_draft',
      userBrief: '写一场试探对话。',
      selection: {
        style: card('style-1', 'style', '克制风格'),
        character: card('character-1', 'character', '沉默角色'),
        scene: card('scene-1', 'scene', '试探场景'),
      },
    })

    expect(prompt).toContain('生成目标：场景草稿')
    expect(prompt).toContain('写一场试探对话')
    expect(prompt).toContain('不要照搬')
  })

  it('routes combination generation through the shared AI task request', () => {
    const request = buildCardCombinationTaskRequest({
      target: 'outline_suggestion',
      userBrief: '生成三幕式建议。',
      selection: {
        style: card('style-1', 'style', '风格'),
        character: undefined,
        scene: card('scene-1', 'scene', '场景'),
      },
    })

    expect(request.task_type).toBe('outline')
    expect(request.target_kind).toBe('paste')
    expect(request.cost_tier).toBe('strong')
    expect(request.attachments?.map((item) => item.ref_id)).toEqual(['style-1', 'scene-1'])
  })
})
