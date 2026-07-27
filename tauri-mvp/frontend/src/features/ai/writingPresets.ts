import type { AiTaskPreset } from '../../api/ai'
import {
  createDefaultControls,
  mergeControls,
  type FocusTaskType,
  type TaskControls,
} from './taskControls'

export type WritingPresetTier = 'common' | 'creative'
export type WritingPresetGenre = 'general' | 'fiction' | 'essay' | 'nonfiction'
export type WritingPresetRequirement =
  | 'viewpoint_or_tense'
  | 'viewpoint_character'
  | 'argument_direction'
  | 'scene_focus'

interface LocalizedCopy {
  zh: string
  en: string
}

export interface WritingPresetDefinition {
  id: string
  taskType: FocusTaskType
  tier: WritingPresetTier
  genres: WritingPresetGenre[]
  name: LocalizedCopy
  description: LocalizedCopy
  guidance: LocalizedCopy
  risk?: LocalizedCopy
  controls: Partial<TaskControls>
  requirements?: WritingPresetRequirement[]
  isDefault?: boolean
}

export type WritingPresetLocale = 'zh' | 'en'

const COMMON_RISK: LocalizedCopy = {
  zh: '会主动改变表达策略。请在结果工作区对照原文后再写回。',
  en: 'This actively changes the writing strategy. Compare it with the original before applying.',
}

export const BUILT_IN_WRITING_PRESETS: WritingPresetDefinition[] = [
  preset('polish-clear', 'polish', 'common', ['general', 'fiction', 'essay', 'nonfiction'], '清楚顺读', 'Clear and Readable', '理清句意和指代，让文字顺畅但不抹平作者语气。', 'Clarify meaning and references while keeping the author voice.', '优先修复含混、拗口、指代不清和不必要的绕句；不新增事实，不把有意的含蓄改成解释。', 'Fix ambiguity, awkward phrasing, unclear references, and unnecessary detours. Add no facts and preserve intentional implication.', {
    polishGoal: 'clarity',
    polishIntensity: 'medium',
    polishRhythm: 'balanced',
    preserveVoice: true,
  }, true),
  preset('polish-tighten', 'polish', 'common', ['general', 'fiction', 'essay', 'nonfiction'], '收紧去赘', 'Tighten and Trim', '删除重复解释、空转过渡和无效修饰。', 'Remove repeated explanation, empty transitions, and weak modifiers.', '压缩重复信息、同义反复、空泛判断和拖沓转折；保留关键事实、情绪转折和必要留白。', 'Compress repeated ideas, redundant phrasing, vague judgments, and slow transitions while preserving facts, emotional turns, and useful silence.', {
    polishGoal: 'clarity',
    polishIntensity: 'strong',
    polishRhythm: 'tight',
    compressRedundancy: true,
  }),
  preset('polish-rhythm', 'polish', 'common', ['fiction', 'essay'], '整理节奏', 'Shape the Rhythm', '调整长短句、停顿和段落推进，不追求统一句型。', 'Shape sentence length, pauses, and paragraph movement without flattening the prose.', '根据语义重心调整长短句、停顿和段落节奏；保留有意的重复、断裂和呼吸感。', 'Adjust sentence length, pauses, and paragraph rhythm around meaning. Preserve deliberate repetition, fragments, and breathing room.', {
    polishGoal: 'rhythm',
    polishRhythm: 'flowing',
    polishIntensity: 'medium',
  }),
  preset('polish-dialogue', 'polish', 'common', ['fiction'], '对话更自然', 'Natural Dialogue', '让对白符合人物关系和当下情境，减少书面腔。', 'Make dialogue fit the characters and moment, with less written-sounding speech.', '只打磨对白及其必要的动作承接：减少解释性台词和完整句堆叠，保留人物口头习惯、回避、停顿和潜台词。', 'Polish dialogue and only the action beats it needs. Reduce explanatory speech and overly complete sentences while preserving verbal habits, avoidance, pauses, and subtext.', {
    polishGoal: 'clarity',
    polishRhythm: 'balanced',
    preserveVoice: true,
  }),
  preset('polish-literary', 'polish', 'creative', ['fiction', 'essay'], '提升文气', 'Heighten the Prose', '增强语言质感、画面和余韵，但避免堆砌辞藻。', 'Increase texture, imagery, and resonance without ornamental excess.', '在不改变事实与视角的前提下，提高用词准确度、画面感和句子余韵；少量强化已有意象，不新增成套比喻。', 'Improve diction, imagery, and resonance without changing facts or viewpoint. Strengthen existing images sparingly; do not introduce chains of new metaphors.', {
    polishGoal: 'literary',
    polishImagery: 'enhance',
    polishIntensity: 'medium',
  }, false, COMMON_RISK),
  preset('polish-restrained', 'polish', 'common', ['fiction', 'essay', 'nonfiction'], '降低用力感', 'Reduce Overwriting', '削弱过满修辞、直接评判和刻意煽情。', 'Reduce heavy rhetoric, direct judgment, and forced emotion.', '把过度解释、拔高、感叹和密集修辞收回来；用更具体、克制的表达保留情绪，不把文字改得冷漠。', 'Pull back over-explanation, elevation, exclamation, and dense rhetoric. Keep emotion through concrete, restrained language without making it cold.', {
    polishGoal: 'restrained',
    polishImagery: 'reduce',
    polishIntensity: 'medium',
  }),

  preset('rewrite-natural', 'rewrite', 'common', ['general', 'fiction', 'essay', 'nonfiction'], '自然换一种说法', 'Natural Rephrase', '保留事实、重点和语气，用更自然的句法重新表达。', 'Keep facts, emphasis, and tone while rephrasing more naturally.', '完整保留原文事实、逻辑关系、叙述视角和情绪强度，重组句法和措辞；不要只做同义词替换。', 'Preserve facts, logic, viewpoint, and emotional intensity. Reshape syntax and diction rather than swapping synonyms.', {
    rewriteDirection: '自然重组表达，保留事实、逻辑、视角和情绪强度',
    sentenceChange: 'medium',
    narrativeTone: '贴近原文',
  }, true),
  preset('rewrite-concise', 'rewrite', 'common', ['general', 'nonfiction', 'essay'], '更简洁直接', 'More Concise', '缩短路径，让核心信息更快到达。', 'Shorten the path so the main point arrives sooner.', '用更直接的结构重写，合并可合并的句子和段落，删除不承担信息或节奏作用的内容；不要牺牲关键限定条件。', 'Rewrite with a more direct structure. Merge where useful and remove material that carries neither information nor rhythm, without losing important qualifications.', {
    rewriteDirection: '更简洁、直接、信息路径更短',
    sentenceChange: 'strong',
    narrativeTone: '克制直接',
  }),
  preset('rewrite-show', 'rewrite', 'creative', ['fiction', 'essay'], '展示而非说明', 'Show Rather Than Explain', '把抽象判断转成可观察的动作、感官和选择。', 'Turn abstract judgment into observable action, sensation, and choice.', '将可被场景承载的抽象说明改为动作、感官、对白、物件或人物选择；不新增改变情节走向的事实，也不要把所有含义都写明。', 'Convert abstract explanation that the scene can carry into action, sensation, dialogue, objects, or choices. Add no plot-changing facts and leave room for implication.', {
    rewriteDirection: '把抽象说明转为可观察的场景证据',
    sentenceChange: 'strong',
    narrativeTone: '贴近原文',
  }, false, COMMON_RISK),
  preset('rewrite-subtext', 'rewrite', 'creative', ['fiction'], '对白与潜台词', 'Dialogue and Subtext', '让人物少说结论，多通过回避、动作和言外之意表达。', 'Let characters state less and reveal more through avoidance, action, and implication.', '重写对白及其动作承接：减少人物直接说出动机和结论，利用停顿、答非所问、动作和语气形成潜台词；保持人物关系和事件事实。', 'Rewrite dialogue and its action beats. Reduce direct statements of motive or conclusion; use pauses, deflection, action, and tone to create subtext while preserving relationships and facts.', {
    rewriteDirection: '强化对白潜台词与人物差异',
    sentenceChange: 'strong',
    narrativeTone: '人物化、含蓄',
  }, false, COMMON_RISK),
  preset('rewrite-literary', 'rewrite', 'creative', ['fiction', 'essay'], '更有文学感', 'More Literary', '重组声音、节奏和意象，让表达更有辨识度。', 'Reshape voice, rhythm, and imagery for a more distinctive literary result.', '在保留事实、视角和核心意象的前提下，重组语言声音、节奏和画面；避免仿写特定在世作者，避免华丽同义替换。', 'Reshape voice, rhythm, and imagery while preserving facts, viewpoint, and key images. Do not imitate a specific living author and avoid ornamental synonym swapping.', {
    rewriteDirection: '增强语言辨识度、节奏和画面',
    sentenceChange: 'strong',
    narrativeTone: '文学但克制',
    keepImagery: true,
  }, false, COMMON_RISK),
  preset('rewrite-viewpoint', 'rewrite', 'creative', ['fiction'], '转换视角或时态', 'Change Viewpoint or Tense', '按明确选择转换叙述视角、视角人物或时态。', 'Convert viewpoint, focal character, or tense according to explicit choices.', '严格按照目标视角、视角人物和目标时态重写；保持事件、人物关系和信息边界，不让新视角知道其不可能知道的事实。', 'Rewrite strictly to the chosen viewpoint, focal character, and tense. Preserve events and relationships, and do not give the new viewpoint knowledge it could not have.', {
    rewriteDirection: '按指定视角或时态转换全文',
    sentenceChange: 'strong',
    narrativeTone: '贴近原文',
  }, false, COMMON_RISK, ['viewpoint_or_tense']),

  preset('expand-action', 'expand', 'common', ['fiction'], '补动作现场', 'Add Action on the Page', '补足人物动作、空间关系和因果衔接。', 'Add character action, spatial relations, and causal continuity.', '把概述中的关键动作落到现场，补足谁在做什么、物体和人物的位置变化、动作之间的因果；不要新增改变情节的事件。', 'Put key summarized actions on the page. Clarify who does what, how people and objects move, and the causal links between actions. Add no plot-changing events.', {
    expandFocus: '人物动作、空间关系和动作因果',
    detailType: '动作、空间、物件',
    sensoryDetail: false,
    expandLength: 'medium',
  }, true),
  preset('expand-psychology', 'expand', 'common', ['fiction', 'essay'], '补心理层次', 'Add Psychological Depth', '补充感受、判断和自我矛盾，不替人物做总结。', 'Add feeling, judgment, and inner contradiction without explaining the character away.', '在关键动作和选择之间补充人物当下的感受、判断、犹豫或自我欺骗；通过具体念头推进，不使用泛泛心理总结。', 'Add immediate feeling, judgment, hesitation, or self-deception between key actions and choices. Use concrete thought rather than generic psychological summary.', {
    expandFocus: '人物当下感受、判断与内在矛盾',
    detailType: '心理、选择、身体反应',
    sensoryDetail: true,
    expandLength: 'medium',
  }),
  preset('expand-atmosphere', 'expand', 'common', ['fiction', 'essay'], '补环境氛围', 'Add Atmosphere', '让环境参与情绪与行动，而不是单独铺景。', 'Let setting participate in emotion and action instead of becoming detached description.', '补充与人物动作、情绪和叙事焦点直接相关的环境细节；让环境发生作用，不写与场面无关的全景介绍。', 'Add setting details directly tied to action, emotion, and narrative focus. Let the environment do work; avoid unrelated panoramic description.', {
    expandFocus: '环境如何影响人物、动作和情绪',
    detailType: '空间、光线、声音、物件',
    sensoryDetail: true,
    expandLength: 'medium',
  }),
  preset('expand-senses', 'expand', 'creative', ['fiction', 'essay'], '补五感细节', 'Add Sensory Detail', '选择最有作用的感官线索，增强现场感。', 'Choose the most useful sensory cues to make the moment present.', '选择两到三种最能服务场面重心的感官线索，写出具体来源和人物反应；不要平均罗列五感，不堆形容词。', 'Choose two or three sensory channels that best serve the scene focus, including their source and the character response. Do not mechanically list all five senses or pile up adjectives.', {
    expandFocus: '现场感与感官证据',
    detailType: '声音、触感、气味、光线、温度',
    sensoryDetail: true,
    expandLength: 'medium',
  }, false, COMMON_RISK),
  preset('expand-argument', 'expand', 'common', ['nonfiction', 'essay'], '补论述层次', 'Develop the Argument', '补足论点、证据、转折和边界条件。', 'Develop claims, evidence, transitions, and qualifications.', '围绕指定论述方向补充必要的理由、例证、反例或限定条件，明确段落之间的逻辑推进；不要虚构数据、来源或引文。', 'Develop the chosen argument direction with reasons, examples, counterpoints, or qualifications, and clarify paragraph logic. Do not invent data, sources, or quotations.', {
    expandFocus: '论点、证据、反例与限定条件',
    detailType: '论证、例证、转折',
    sensoryDetail: false,
    expandLength: 'medium',
  }, false, undefined, ['argument_direction']),
  preset('expand-scene', 'expand', 'creative', ['fiction'], '放慢并扩成场面', 'Slow Down into a Scene', '把概述段落展开成可经历的场面。', 'Turn summary into an experienced scene.', '围绕指定场面重心放慢叙事，用动作、空间、对白、感官和即时反应展开；保持原有事件结果，不新增支线。', 'Slow the narrative around the chosen scene focus using action, space, dialogue, sensation, and immediate response. Preserve the original outcome and add no subplot.', {
    expandFocus: '把概述展开为完整场面',
    detailType: '动作、对白、空间、即时反应',
    sensoryDetail: true,
    expandLength: 'long',
  }, false, COMMON_RISK, ['scene_focus']),

  preset('continue-natural', 'continue', 'common', ['general', 'fiction', 'essay', 'nonfiction'], '自然接下去', 'Continue Naturally', '承接最后的语气、事实和节奏，向前写一个自然单位。', 'Carry forward the latest tone, facts, and rhythm for one natural unit.', '从最后一句的动作、问题、意象或论点自然接续，保持视角、时态、人物知识边界和语言密度；不要突然转折或收尾。', 'Continue from the final action, question, image, or claim. Preserve viewpoint, tense, knowledge boundaries, and prose density; do not force a sudden turn or ending.', {
    continuationMode: '承接最后一句自然继续',
    continueLength: 'medium',
    pacing: '适中',
    emotionalDirection: '顺着当前情绪自然推进',
  }, true),
  preset('continue-scene', 'continue', 'common', ['fiction'], '推进场面一步', 'Move the Scene One Beat', '让人物做出下一步动作或选择，形成新的局面。', 'Have the character take the next action or choice and create a new beat.', '只推进一个清楚的场面节拍：回应当前刺激，让人物采取动作或作出选择，并留下可继续写的局面；不要跳过重要过程。', 'Advance one clear scene beat: respond to the current stimulus, let a character act or choose, and leave a playable next state. Do not skip important process.', {
    continuationMode: '推进当前场面一个清楚节拍',
    continueLength: 'medium',
    pacing: '稳步推进',
    emotionalDirection: '让动作带出下一步变化',
  }),
  preset('continue-dialogue', 'continue', 'common', ['fiction'], '延续对白', 'Continue the Dialogue', '延续人物声音、关系张力和言外之意。', 'Continue character voices, relational tension, and implication.', '从当前对白继续一轮到两轮，保持人物各自的说话方式和信息边界；让动作、停顿或回避承担潜台词，不用对白解释一切。', 'Continue one or two exchanges while preserving each character voice and knowledge boundary. Let action, pauses, and avoidance carry subtext instead of explaining everything in speech.', {
    continuationMode: '延续对白并保持人物声音',
    continueLength: 'short',
    pacing: '对话节奏',
    emotionalDirection: '维持并推进关系张力',
  }),
  preset('continue-emotion', 'continue', 'creative', ['fiction', 'essay'], '压深情绪', 'Deepen the Emotion', '不拔高结论，让情绪通过动作、感官和选择继续下沉。', 'Deepen emotion through action, sensation, and choice rather than declaration.', '沿当前情绪向更具体、更矛盾的一层推进，用身体反应、注意力偏移、动作或选择呈现；不要直接宣布人物感悟。', 'Move the current emotion into a more specific or conflicted layer through bodily response, shifted attention, action, or choice. Do not announce the character lesson.', {
    continuationMode: '让情绪通过动作和选择继续下沉',
    continueLength: 'medium',
    pacing: '放慢',
    emotionalDirection: '更具体、更矛盾，但不拔高',
  }, false, COMMON_RISK),
  preset('continue-argument', 'continue', 'common', ['nonfiction', 'essay'], '顺着论点继续', 'Continue the Argument', '承接当前论点，补充下一层理由、例证或限定。', 'Carry the current claim into the next reason, example, or qualification.', '承接当前段落的论点和语气，推进一个逻辑层次，可补理由、例证、反例或限定；不要重复前文，不虚构来源。', 'Carry the current claim and tone into one further logical layer using a reason, example, counterpoint, or qualification. Do not repeat the previous paragraph or invent sources.', {
    continuationMode: '顺着当前论点推进一个逻辑层次',
    continueLength: 'medium',
    pacing: '清楚推进',
    emotionalDirection: '保持当前论述语气',
  }),
  preset('continue-close', 'continue', 'common', ['general', 'fiction', 'essay', 'nonfiction'], '收住这一段', 'Bring the Passage to Rest', '完成当前段落或小节的局部收束，不替整篇文章总结。', 'Give the current passage a local landing without summarizing the whole piece.', '为当前段落或小节写出克制的局部收束，回应已有动作、意象或论点；不做全文总结，不突然升华，不强行圆满。', 'Give the current paragraph or section a restrained local landing by answering an existing action, image, or claim. Do not summarize the whole work, force elevation, or manufacture closure.', {
    continuationMode: '为当前段落或小节做局部收束',
    continueLength: 'short',
    pacing: '放缓收束',
    emotionalDirection: '克制、留有余地',
  }),
  preset('continue-foreshadow', 'continue', 'creative', ['fiction'], '埋下伏笔', 'Plant Foreshadowing', '在正常推进中放入可回收但不过分醒目的线索。', 'Place a recoverable but unobtrusive clue inside normal scene movement.', '在推进当前场面的同时放入一个可回收线索，可借物件、反常动作、信息缺口或重复意象呈现；不要解释其意义，不新增破坏既有设定的事实。', 'While advancing the scene, plant one recoverable clue through an object, unusual action, information gap, or recurring image. Do not explain its meaning or add facts that break established continuity.', {
    continuationMode: '推进场面并埋入一个克制伏笔',
    continueLength: 'medium',
    pacing: '正常推进',
    emotionalDirection: '表面自然，留下轻微不安或疑问',
  }, false, COMMON_RISK),
]

function preset(
  id: string,
  taskType: FocusTaskType,
  tier: WritingPresetTier,
  genres: WritingPresetGenre[],
  zhName: string,
  enName: string,
  zhDescription: string,
  enDescription: string,
  zhGuidance: string,
  enGuidance: string,
  controls: Partial<TaskControls>,
  isDefault = false,
  risk?: LocalizedCopy,
  requirements?: WritingPresetRequirement[],
): WritingPresetDefinition {
  return {
    id,
    taskType,
    tier,
    genres,
    name: { zh: zhName, en: enName },
    description: { zh: zhDescription, en: enDescription },
    guidance: { zh: zhGuidance, en: enGuidance },
    risk,
    controls,
    requirements,
    isDefault,
  }
}

export function writingPresetCopy(copy: LocalizedCopy | undefined, locale: string): string {
  if (!copy) return ''
  return locale === 'en' ? copy.en : copy.zh
}

export function presetsForTask(taskType: FocusTaskType): WritingPresetDefinition[] {
  return BUILT_IN_WRITING_PRESETS.filter((item) => item.taskType === taskType)
}

export function defaultPresetForTask(taskType: FocusTaskType): WritingPresetDefinition {
  const values = presetsForTask(taskType)
  return values.find((item) => item.isDefault) ?? values[0]
}

export function controlsForBuiltInPreset(
  presetValue: WritingPresetDefinition,
  locale: string,
): TaskControls {
  return mergeControls({
    ...createDefaultControls(),
    ...presetValue.controls,
    presetGuidance: writingPresetCopy(presetValue.guidance, locale),
  })
}

export function customPresetControls(presetValue: AiTaskPreset): TaskControls {
  return mergeControls(presetValue.controls)
}

export function missingPresetRequirements(
  presetValue: WritingPresetDefinition | null,
  controls: TaskControls,
): WritingPresetRequirement[] {
  if (!presetValue?.requirements?.length) return []
  return presetValue.requirements.filter((requirement) => {
    if (requirement === 'viewpoint_or_tense') {
      return controls.targetViewpoint === 'keep' && controls.targetTense === 'keep'
    }
    if (requirement === 'viewpoint_character') {
      return controls.targetViewpoint === 'third_limited' && !controls.viewpointCharacter.trim()
    }
    if (requirement === 'argument_direction') return !controls.argumentDirection.trim()
    if (requirement === 'scene_focus') return !controls.sceneFocus.trim()
    return false
  })
}
