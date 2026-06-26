import type { AiContextAttachment, AiTaskRequest } from '../../api/ai'
import type { AiCard } from '../../api/aiCards'

export type CardCombinationTarget = 'scene_draft' | 'paragraph_draft' | 'outline_suggestion'

export interface CardCombinationSelection {
  style?: AiCard | null
  character?: AiCard | null
  scene?: AiCard | null
}

export interface CardCombinationPromptOptions {
  target: CardCombinationTarget
  userBrief: string
  selection: CardCombinationSelection
}

export const CARD_COMBINATION_TARGETS: { id: CardCombinationTarget; label: string }[] = [
  { id: 'scene_draft', label: '场景草稿' },
  { id: 'paragraph_draft', label: '段落草稿' },
  { id: 'outline_suggestion', label: '大纲建议' },
]

export function cardAttachment(card: AiCard): AiContextAttachment {
  return {
    kind: `ai_card:${card.card_type}`,
    ref_id: card.id,
    name: card.title || '未命名 AI 卡片',
    body: card.content || '',
  }
}

export function selectedCards(selection: CardCombinationSelection): AiCard[] {
  return [selection.style, selection.character, selection.scene].filter(Boolean) as AiCard[]
}

export function buildCardCombinationPrompt(options: CardCombinationPromptOptions): string {
  const targetLabel = CARD_COMBINATION_TARGETS.find((item) => item.id === options.target)?.label || '写作草稿'
  const brief = options.userBrief.trim() || '请根据已选择的卡片生成一段可继续编辑的内容。'
  const selected = selectedCards(options.selection)
  const cardList = selected.length
    ? selected.map((card) => `- ${card.card_type}: ${card.title}`).join('\n')
    : '- 未选择卡片'

  return [
    `生成目标：${targetLabel}`,
    '',
    '用户意图：',
    brief,
    '',
    '已选择卡片：',
    cardList,
    '',
    '要求：',
    '- 综合风格卡、人物卡、场景卡，不要逐条复述卡片内容。',
    '- 输出必须是可直接进入写作流程的草稿或建议。',
    '- 不要声称这是最终稿；保留作者可继续修改的空间。',
    '- 不要照搬【参考原文（可选）】里的句子。',
  ].join('\n')
}

export function buildCardCombinationTaskRequest(options: CardCombinationPromptOptions): AiTaskRequest {
  const cards = selectedCards(options.selection)
  const attachments = cards.map(cardAttachment)
  const prompt = buildCardCombinationPrompt(options)
  const taskType: AiTaskRequest['task_type'] = options.target === 'outline_suggestion' ? 'outline' : 'continue'
  const maxOutputChars = options.target === 'outline_suggestion' ? 3000 : options.target === 'scene_draft' ? 4200 : 2200

  return {
    task_type: taskType,
    text: prompt,
    target_kind: 'paste',
    target_ref_id: null,
    style: '把 AI 卡片组合成新的原创写作内容',
    extra_instructions: '只输出生成结果，不要解释你如何使用了卡片。',
    preserve_meaning: false,
    preserve_voice: true,
    attachments,
    max_output_chars: maxOutputChars,
    cost_tier: 'strong',
  }
}
