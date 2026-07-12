"""Task-aware prompt construction for the AI workspace.

Maps an :class:`AiTaskRequest` to a list of ``{role, content}`` dicts the
provider can pass to the Responses API.

Design notes:
* Each task type has a system prompt that names the role + safety bounds.
* The user prompt is composed from: target text, attachments, task-specific
  controls, hard constraints (forbid / must keep), free-form extra
  instructions, and an output-shape hint.
* Diagnostic and library-QA tasks are explicitly told to return JSON so
  the UI can render structured findings; they also explicitly cite
  attachment names so :class:`AiTaskService` can surface citations.
"""

from __future__ import annotations

from typing import Dict, List

from writer.app.locale import LOCALE_ZH_CN, current_locale
from writer.domain.enums import AiTaskType
from writer.services.ai.task_types import AiContextAttachment, AiTaskRequest


_REWRITE_TASKS = {
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
}
_SPECIMEN_GUIDED_TASKS = _REWRITE_TASKS | {AiTaskType.STYLE_TRANSFER}

_VOICE_PRESERVE_TASKS = _REWRITE_TASKS | {AiTaskType.STYLE_TRANSFER}
_STYLE_GUIDED_TASKS = {AiTaskType.POLISH, AiTaskType.STYLE_TRANSFER}


_EN_SYSTEM: Dict[AiTaskType, str] = {
    AiTaskType.POLISH: (
        "You are a prose polishing editor. Improve wording, rhythm, clarity, "
        "and prose texture while preserving the subject text's facts, scene, "
        "and narrative stance. You may follow style instructions, author "
        "shortcuts, and style specimens, but you must not add new plot, facts, "
        "characters, or settings. Return the full polished text only."
    ),
    AiTaskType.EXPAND: (
        "You are an expansion editor. Expand the given passage from within "
        "its existing premise by adding sensory detail, interiority, action "
        "texture, atmosphere, or implied context. Do not continue into later "
        "plot beats, do not change the premise, and do not invent concrete "
        "facts that the text does not support. Return the full expanded text."
    ),
    AiTaskType.CONTINUE: (
        "You are a continuation writer. Continue from the final line of the "
        "subject text in the same voice, tense, and scene logic. Do not rewrite, "
        "summarize, or repeat the existing text. Return ONLY the new continuation."
    ),
    AiTaskType.STYLE_TRANSFER: (
        "You are a style transfer assistant. Rewrite the given text so it "
        "matches the requested style profile while preserving the original "
        "meaning and named entities. Return only the rewritten text."
    ),
    AiTaskType.SUMMARIZE: (
        "You are an editorial summarizer. Produce STRICT JSON with schema:\n"
        '{"summary": str, "key_facts": [str], "themes": [str], '
        '"keeper_lines": [str]}\n'
        "Be faithful to the text and do not editorialize. Return JSON only."
    ),
    AiTaskType.OUTLINE: (
        "You are an outlining editor. Produce STRICT JSON with schema:\n"
        '{"outline": [{"title": str, "children": [same]}]}\n'
        "Organize the existing material by the requested outline mode. "
        "Do not invent new content. Return JSON only."
    ),
    AiTaskType.TITLE: (
        "You are a title editor. Produce STRICT JSON with schema:\n"
        '{"groups": [{"category": str, "titles": '
        '[{"title": str, "reason": str}]}]}\n'
        "Group candidates by title style. Return JSON only."
    ),
    AiTaskType.STRUCTURE_DIAGNOSE: (
        "You are a structural editor. Analyse the given text and report "
        "issues in pacing, paragraph order, setup/payoff, opening, and ending. "
        "Output STRICT JSON with the schema:\n"
        '{"issues": [{"location": str, "excerpt": str, '
        '"problem": str, "impact": str, "suggestion": str, '
        '"priority": str}], "summary": str}\n'
        "Return JSON only, no preface."
    ),
    AiTaskType.CONSISTENCY_CHECK: (
        "You are a consistency editor. Look for contradictions in facts, "
        "characters, timeline, setting rules, and tone in the given text. "
        "Output STRICT JSON:\n"
        '{"issues": [{"kind": str, "excerpt": str, '
        '"problem": str, "risk": str, "suggestion": str}], '
        '"summary": str}\n'
        "If no issues are found, issues should be an empty list and "
        "summary should explicitly say so. Return JSON only."
    ),
    AiTaskType.LIBRARY_QA: (
        "You are a writing-library Q&A assistant. Answer the user's "
        "question USING ONLY the provided source attachments. If the "
        "answer is not in the sources, say so explicitly. Output STRICT "
        "JSON:\n"
        '{"answer": str, "citations": [{"name": str, '
        '"excerpt": str}], "unconfirmed": [str]}\n'
        "Citations MUST quote the source attachment names verbatim. "
        "Return JSON only."
    ),
}

_ZH_SYSTEM: Dict[AiTaskType, str] = {
    AiTaskType.POLISH: (
        "你是一位散文润色编辑。改善措辞、节奏、清晰度和文风质感，同时保留原文事实、"
        "场景和叙述视角。可以遵循风格要求、作家快捷预设和文脉标本，但不得新增剧情、"
        "事实、人物或设定。只返回完整润色后的正文。"
    ),
    AiTaskType.EXPAND: (
        "你是一位扩写编辑。围绕原文已经存在的前提，补充感官细节、心理活动、动作质感、"
        "环境氛围或可被原文暗示的背景。不要写后续剧情，不要改变原始前提，"
        "不要新增没有依据的具体事实。只返回完整扩写后的正文。"
    ),
    AiTaskType.CONTINUE: (
        "你是一位续写作者。从原文最后一句接着写，保持声音、时态和场景逻辑。"
        "不要重写、总结或复述已有内容。只返回新增续写内容。"
    ),
    AiTaskType.STYLE_TRANSFER: (
        "你是风格迁移助手。将给定文本改写为指定风格，同时保留原意与专有名词。只返回改写后的文本。"
    ),
    AiTaskType.SUMMARIZE: (
        "你是编辑摘要助手。严格输出 JSON：\n"
        '{"summary": 字符串, "key_facts": [字符串], "themes": [字符串], '
        '"keeper_lines": [字符串]}\n'
        "忠实于原文，不发表评论。只返回 JSON。"
    ),
    AiTaskType.OUTLINE: (
        "你是提纲编辑。严格输出 JSON：\n"
        '{"outline": [{"title": 字符串, "children": [同结构]}]}\n'
        "按用户要求的提纲模式组织已有内容，不要新增内容。只返回 JSON。"
    ),
    AiTaskType.TITLE: (
        "你是标题编辑。严格输出 JSON：\n"
        '{"groups": [{"category": 字符串, "titles": '
        '[{"title": 字符串, "reason": 字符串}]}]}\n'
        "按标题风格分组给出候选标题。只返回 JSON。"
    ),
    AiTaskType.STRUCTURE_DIAGNOSE: (
        "你是结构编辑。分析文本中的节奏、段落顺序、铺垫回收、开头和结尾问题。"
        "严格输出 JSON：\n"
        '{"issues": [{"location": 字符串, "excerpt": 字符串, '
        '"problem": 字符串, "impact": 字符串, "suggestion": 字符串, '
        '"priority": 字符串}], "summary": 字符串}\n'
        "只返回 JSON。"
    ),
    AiTaskType.CONSISTENCY_CHECK: (
        "你是一致性编辑。查找文本中的人物、时间线、事实、语气和设定矛盾。严格输出 JSON：\n"
        '{"issues": [{"kind": 字符串, "excerpt": 字符串, '
        '"problem": 字符串, "risk": 字符串, "suggestion": 字符串}], '
        '"summary": 字符串}\n'
        "若没有问题，issues 为空数组，summary 明确说明。只返回 JSON。"
    ),
    AiTaskType.LIBRARY_QA: (
        "你是写作库问答助手。仅基于提供的来源附件回答问题。如答案不在来源中，"
        "明确说明。严格输出 JSON：\n"
        '{"answer": 字符串, "citations": [{"name": 字符串, '
        '"excerpt": 字符串}], "unconfirmed": [字符串]}\n'
        "citations 中的 name 必须与来源附件名称完全一致。只返回 JSON。"
    ),
}


# Tasks whose output we expect to be structured JSON.
STRUCTURED_TASKS = {
    AiTaskType.SUMMARIZE,
    AiTaskType.OUTLINE,
    AiTaskType.TITLE,
    AiTaskType.STRUCTURE_DIAGNOSE,
    AiTaskType.CONSISTENCY_CHECK,
    AiTaskType.LIBRARY_QA,
}


class TaskPromptBuilder:
    def system_prompt(self, task_type: AiTaskType) -> str:
        prompts = _ZH_SYSTEM if current_locale() == LOCALE_ZH_CN else _EN_SYSTEM
        try:
            return prompts[task_type]
        except KeyError as exc:  # pragma: no cover
            raise ValueError(f"Unknown task type: {task_type}") from exc

    def build_messages(self, request: AiTaskRequest) -> List[Dict[str, str]]:
        is_zh = current_locale() == LOCALE_ZH_CN
        system = self.system_prompt(request.task_type)
        if request.task_type is AiTaskType.POLISH:
            system += _polish_guidance(request, is_zh)
        if request.style:
            if request.task_type in _STYLE_GUIDED_TASKS:
                system += _style_guidance(is_zh)
            if request.preserve_voice and request.task_type in _VOICE_PRESERVE_TASKS:
                system += _style_voice_guidance(is_zh)
        elif request.preserve_voice and request.task_type in _VOICE_PRESERVE_TASKS:
            system += (
                " 严格保留原文的叙述声音。" if is_zh else " Strictly preserve the author's voice."
            )
        if not request.preserve_meaning and request.task_type in _VOICE_PRESERVE_TASKS:
            system += (
                " 如用户明确要求，可以调整原意。"
                if is_zh
                else " You MAY adjust the original meaning if requested."
            )
        # Add specimen constraints when style specimens are attached.
        has_specimens = any(a.kind == "style_specimen" for a in (request.attachments or []))
        if has_specimens and request.task_type in _SPECIMEN_GUIDED_TASKS:
            system += _specimen_constraint(is_zh)

        user_parts: List[str] = []
        if request.style:
            user_parts.append(_task_instruction_label(request.task_type, is_zh) + request.style)
        if request.intensity:
            user_parts.append(_task_intensity_label(request.task_type, is_zh) + request.intensity)
        if request.must_keep_terms:
            user_parts.append(
                (
                    "必须保留的词语（不要改写掉）："
                    if is_zh
                    else "Must-keep terms (do not paraphrase away): "
                )
                + ", ".join(request.must_keep_terms)
            )
        if request.forbid_terms:
            user_parts.append(
                ("禁用词（不要出现）：" if is_zh else "Forbidden terms (do not include): ")
                + ", ".join(request.forbid_terms)
            )
        if request.extra_instructions:
            user_parts.append(
                ("附加要求：" if is_zh else "Extra instructions: ") + request.extra_instructions
            )
        if request.max_output_chars:
            user_parts.append(
                (
                    f"输出尽量控制在约 {request.max_output_chars} 个字符以内。"
                    if is_zh
                    else f"Keep the output within about {request.max_output_chars} characters."
                )
            )

        if request.task_type in _REWRITE_TASKS:
            user_parts.append(_rewrite_output_contract(is_zh))
        if request.task_type is AiTaskType.POLISH:
            user_parts.append(_polish_output_guidance(request, is_zh))
        elif request.task_type is AiTaskType.EXPAND:
            user_parts.append(_expand_output_guidance(request, is_zh))
        elif request.task_type is AiTaskType.CONTINUE:
            user_parts.append(_continue_output_guidance(is_zh))

        if request.attachments:
            user_parts.append(_format_attachments(request.attachments, is_zh=is_zh))

        user_parts.append(("待处理文本：\n" if is_zh else "Subject text:\n") + request.text)

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]


def _format_attachments(attachments: List[AiContextAttachment], *, is_zh: bool) -> str:
    """Render attachments as a labelled source pack the model can cite by name."""
    blocks = [
        "来源附件（需要时按名称引用）："
        if is_zh
        else "Source attachments (cite by name when relevant):"
    ]
    for att in attachments:
        header = f"[{att.kind}] {att.name}"
        body = att.body.strip()
        if not body:
            continue
        blocks.append(f"--- {header} ---\n{body}")
    return "\n\n".join(blocks)


def _style_guidance(is_zh: bool) -> str:
    if is_zh:
        return (
            " 如果提供了风格要求，请把它视为一个自由输入的改写提示词，而不是固定预设。"
            "无论里面写了多少作家名字、写法特征或气质要求，都直接落实到一版最终正文里，"
            "不要拆成按作家分别输出的多个版本。"
        )
    return (
        " If a style instruction is provided, treat it as a freeform rewriting prompt, "
        "not as a fixed preset. Even if it names multiple authors or multiple stylistic "
        "traits, apply them directly in a single final passage instead of producing "
        "author-by-author variants."
    )


def _style_voice_guidance(is_zh: bool) -> str:
    if is_zh:
        return " 保留原句的核心意思、观察角度和场景事实，但允许文气向目标风格靠拢。"
    return (
        " Preserve the original meaning, scene facts, and narrative stance, but allow "
        "the prose texture to move toward the requested style."
    )


def _task_instruction_label(task_type: AiTaskType, is_zh: bool) -> str:
    if is_zh:
        labels = {
            AiTaskType.POLISH: "润色目标 / 风格：",
            AiTaskType.EXPAND: "扩写方向：",
            AiTaskType.CONTINUE: "续写方向 / 长度：",
            AiTaskType.STYLE_TRANSFER: "目标风格：",
            AiTaskType.SUMMARIZE: "摘要模式：",
            AiTaskType.OUTLINE: "提纲模式：",
            AiTaskType.TITLE: "标题风格：",
            AiTaskType.STRUCTURE_DIAGNOSE: "诊断重点：",
            AiTaskType.CONSISTENCY_CHECK: "一致性重点：",
            AiTaskType.LIBRARY_QA: "回答重点：",
        }
        return labels.get(task_type, "任务要求：")
    labels = {
        AiTaskType.POLISH: "Polish goal / style: ",
        AiTaskType.EXPAND: "Expansion direction: ",
        AiTaskType.CONTINUE: "Continuation direction / length: ",
        AiTaskType.STYLE_TRANSFER: "Target style: ",
        AiTaskType.SUMMARIZE: "Summary mode: ",
        AiTaskType.OUTLINE: "Outline mode: ",
        AiTaskType.TITLE: "Title style: ",
        AiTaskType.STRUCTURE_DIAGNOSE: "Diagnosis focus: ",
        AiTaskType.CONSISTENCY_CHECK: "Consistency focus: ",
        AiTaskType.LIBRARY_QA: "Answer focus: ",
    }
    return labels.get(task_type, "Task instruction: ")


def _task_intensity_label(task_type: AiTaskType, is_zh: bool) -> str:
    if is_zh:
        labels = {
            AiTaskType.POLISH: "润色幅度：",
            AiTaskType.EXPAND: "细节密度：",
        }
        return labels.get(task_type, "强度：")
    labels = {
        AiTaskType.POLISH: "Polish scope: ",
        AiTaskType.EXPAND: "Detail density: ",
    }
    return labels.get(task_type, "Intensity: ")


def _rewrite_output_contract(is_zh: bool) -> str:
    if is_zh:
        return "\n".join(
            [
                "输出要求：",
                "- 润色和扩写返回完整正文；续写只返回新增续写内容。",
                "- 不要标题、不要解释、不要分点、不要附带风格解析。",
                "- 即使风格要求里写了多个作家或多个特征，也只返回一版最终结果。",
                "- 直接输出正文，不要加引号。",
            ]
        )
    return "\n".join(
        [
            "Output rules:",
            "- Polish and expand return the full resulting text; "
            "continue returns only the new continuation.",
            "- No heading, no explanation, no bullet list, and no style analysis.",
            "- Even if the style instruction mentions multiple authors or traits, "
            "still return only one final result.",
            "- Output the prose directly, with no quotation marks.",
        ]
    )


def _polish_guidance(request: AiTaskRequest, is_zh: bool) -> str:
    intensity = (request.intensity or "").strip().lower()
    has_style = bool((request.style or "").strip())
    if is_zh:
        if intensity == "strong":
            return (
                " 这次润色允许做较大幅度的句式重组、节奏重塑和意象增强，"
                "但仍然只做润色：不要新增情节、人物、设定或具体事实，不要把它当作扩写。"
            )
        if intensity == "medium":
            return (
                " 这次润色不要只做同义词替换。请做明显的句式和节奏调整；"
                "可以增强语言质感，但不要增加新的信息点或后续剧情。"
            )
        if has_style:
            return " 如果给了风格要求，不要只做表面润色；即使保持克制，也要让语言纹理明显向该风格靠拢。"
        return ""
    if intensity == "strong":
        return (
            " This polish pass may substantially recast sentence structure, rhythm, and imagery. "
            "It is still a polish pass: do not add plot, characters, settings, or concrete facts, and do not treat it as expansion."
        )
    if intensity == "medium":
        return (
            " This polish pass should do more than synonym substitution. Make noticeable changes to sentence shape and cadence; "
            "you may enrich the prose texture, but do not add new information points or later plot."
        )
    if has_style:
        return " If a style instruction is present, do more than surface polish; even in a restrained pass, the prose texture should clearly move toward that style."
    return ""


def _polish_output_guidance(request: AiTaskRequest, is_zh: bool) -> str:
    intensity = (request.intensity or "").strip().lower()
    has_style = bool((request.style or "").strip())
    if is_zh:
        if intensity in {"medium", "strong"} and has_style:
            return (
                "润色补充要求：把语言打磨到目标风格，但不要用润色承担扩写；"
                "保留原文的信息范围，不新增人物、事件、设定或后续动作。"
            )
        if intensity in {"medium", "strong"}:
            return "润色补充要求：做明显改写，不要停留在最小幅度修辞替换。"
        return ""
    if intensity in {"medium", "strong"} and has_style:
        return (
            "Polish addendum: move the prose toward the requested style, but do not use polishing as expansion; "
            "keep the same information scope and do not add characters, events, settings, or later action."
        )
    if intensity in {"medium", "strong"}:
        return "Polish addendum: make a noticeable rewrite, not just the smallest possible wording swap."
    return ""


def _expand_output_guidance(request: AiTaskRequest, is_zh: bool) -> str:
    intensity = (request.intensity or "").strip().lower()
    if is_zh:
        if intensity == "strong":
            return (
                "扩写补充要求：把细节密度拉高，充分补足感官、动作、心理和环境层次；"
                "但所有新增内容都必须能由原文当前场景或论述支撑，不要推进到下一段剧情。"
            )
        if intensity == "medium":
            return (
                "扩写补充要求：明显增加当前段落内部的细节密度，让画面、动作或心理更饱满；"
                "不要只换说法，也不要写到原文结尾之后。"
            )
        return (
            "扩写补充要求：只扩充原文当前场景/论述内部的感官、心理、环境、动作或背景质感；"
            "不要从结尾往后续写，不要改变原始前提。"
        )
    if intensity == "strong":
        return (
            "Expansion addendum: push the detail density high with substantial sensory, action, "
            "interior, and atmospheric layering, but keep every addition grounded in the current "
            "scene or argument and do not advance into the next plot beat."
        )
    if intensity == "medium":
        return (
            "Expansion addendum: noticeably increase the detail density inside the current passage "
            "so the scene, action, or interiority feels fuller; do more than rephrase, and do not "
            "continue beyond the ending."
        )
    return (
        "Expansion addendum: add sensory, interior, atmospheric, action, or contextual detail "
        "inside the current scene/argument only; do not continue beyond the ending or change the premise."
    )


def _continue_output_guidance(is_zh: bool) -> str:
    if is_zh:
        return (
            "续写补充要求：只输出原文之后的新内容；不要包含、改写或摘要原文。"
            "按续写方向和长度控制节奏。"
        )
    return (
        "Continuation addendum: output only new content after the source text; do not include, "
        "rewrite, or summarize the source. Use the continuation direction and length to control pacing."
    )


def _specimen_constraint(is_zh: bool) -> str:
    """Constraint injected into the system prompt when style specimens are attached."""
    if is_zh:
        return (
            "\n\n【文脉标本使用规则】已为你提供若干文脉标本（style_specimen）作为风格、"
            "意象或手法参考。请严格遵守以下规则：\n"
            "1. 不得照搬标本中的原句或原段，哪怕改动极小；\n"
            "2. 不得将标本中的具体事实、专有名词或人物移植到输出文本；\n"
            "3. 只借鉴标本的文风肌理、意象营造方式和叙述手法，将其化入你的输出；\n"
            "4. 根据每条标本的用途、标签和作者备注，自行判断本轮真正相关的借鉴方向；\n"
            "5. 多个标本不要机械混合；只吸收与本轮任务相关的部分；\n"
            "6. 最终输出必须在事实、视角和作者明确要求上忠实于待处理文本，而非标本。"
        )
    return (
        "\n\n[Style Specimen Usage Rules] You have been provided with one or more style"
        " specimens as reference for prose style, imagery, or technique. Follow these"
        " rules strictly:\n"
        "1. Do NOT copy sentences or passages from the specimens verbatim or near-verbatim.\n"
        "2. Do NOT transplant specific facts, named entities, or characters from a specimen"
        " into the output.\n"
        "3. Borrow ONLY the prose texture, imagery patterns, and narrative technique."
        " Absorb them into your output without direct quotation.\n"
        "4. Use each specimen's purpose, tags, and author note to infer what is relevant"
        " to this run.\n"
        "5. Do not mechanically blend every specimen; use only the aspects relevant to"
        " the current task.\n"
        "6. The output must remain faithful to the subject text's facts, point of view,"
        " and the author's explicit instructions, not the specimens."
    )
