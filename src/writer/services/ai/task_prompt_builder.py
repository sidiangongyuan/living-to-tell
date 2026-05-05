"""Task-aware prompt construction (M10A).

Maps an :class:`AiTaskRequest` to a list of ``{role, content}`` dicts the
provider can pass to the Responses API.

Design notes:
* Each task type has a system prompt that names the role + safety bounds.
* The user prompt is composed from: target text, attachments, optional
  cards, hard constraints (forbid / must keep), free-form extra
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
    AiTaskType.STYLE_TRANSFER,
}


_EN_SYSTEM: Dict[AiTaskType, str] = {
    AiTaskType.POLISH: (
        "You are a restrained prose polishing assistant. Lightly improve "
        "rhythm, clarity, and word choice while preserving meaning, tone, "
        "and the author's voice. Do not add new facts. Return only the "
        "rewritten text, no preface, no commentary."
    ),
    AiTaskType.EXPAND: (
        "You are a careful writing assistant. Expand the given passage "
        "with sensory detail, reflection, or context that is consistent "
        "with the author's voice and existing content. Do not invent "
        "contradicting facts. Return only the expanded text."
    ),
    AiTaskType.CONTINUE: (
        "You are a careful writing assistant. Continue the given passage "
        "in the same voice, register, and tense. Pick up exactly where "
        "the text leaves off; do not repeat the existing content. Return "
        "only the new continuation."
    ),
    AiTaskType.STYLE_TRANSFER: (
        "You are a style transfer assistant. Rewrite the given text so it "
        "matches the requested style profile while preserving the original "
        "meaning and named entities. Return only the rewritten text."
    ),
    AiTaskType.SUMMARIZE: (
        "You are a summarization assistant. Produce a concise, faithful "
        "summary of the given text. Do not editorialize. Return only the "
        "summary."
    ),
    AiTaskType.OUTLINE: (
        "You are an outlining assistant. Produce a hierarchical outline "
        "of the given text in plain text using indentation and dashes. "
        "Return only the outline."
    ),
    AiTaskType.TITLE: (
        "You are a title generator. Suggest 3–5 candidate titles for the "
        "given text, one per line, no numbering."
    ),
    AiTaskType.STRUCTURE_DIAGNOSE: (
        "You are a structural editor. Analyse the given text and report "
        "structural issues. Output STRICT JSON with the schema:\n"
        "{\"issues\": [{\"location\": str, \"excerpt\": str, "
        "\"problem\": str, \"suggestion\": str}], \"summary\": str}\n"
        "Return JSON only, no preface."
    ),
    AiTaskType.CONSISTENCY_CHECK: (
        "You are a consistency editor. Look for contradictions in facts, "
        "names, timeline, or tone in the given text. Output STRICT JSON:\n"
        "{\"issues\": [{\"kind\": str, \"excerpt\": str, "
        "\"problem\": str, \"suggestion\": str}], \"summary\": str}\n"
        "If no issues are found, issues should be an empty list and "
        "summary should explicitly say so. Return JSON only."
    ),
    AiTaskType.LIBRARY_QA: (
        "You are a writing-library Q&A assistant. Answer the user's "
        "question USING ONLY the provided source attachments. If the "
        "answer is not in the sources, say so explicitly. Output STRICT "
        "JSON:\n"
        "{\"answer\": str, \"citations\": [{\"name\": str, "
        "\"excerpt\": str}]}\n"
        "Citations MUST quote the source attachment names verbatim. "
        "Return JSON only."
    ),
}

_ZH_SYSTEM: Dict[AiTaskType, str] = {
    AiTaskType.POLISH: (
        "你是一位克制的散文润色助手。在保留原意、情感基调和作者声音的前提下，"
        "轻微改善节奏、清晰度和用词。不要添加新事实。只返回改写后的文本。"
    ),
    AiTaskType.EXPAND: (
        "你是一位细心的写作助手。在与作者声音和现有内容一致的前提下，用更多"
        "感官细节、反思或背景扩展给定段落。不要虚构与原文相矛盾的事实。"
        "只返回扩展后的文本。"
    ),
    AiTaskType.CONTINUE: (
        "你是一位细心的写作助手。以相同声音、语气和时态续写给定段落，从结尾"
        "处接着写，不要重复现有内容。只返回新续写的文本。"
    ),
    AiTaskType.STYLE_TRANSFER: (
        "你是风格迁移助手。将给定文本改写为指定风格，同时保留原意与专有名词。"
        "只返回改写后的文本。"
    ),
    AiTaskType.SUMMARIZE: (
        "你是摘要助手。为给定文本生成简洁、忠实的摘要，不发表评论。只返回摘要。"
    ),
    AiTaskType.OUTLINE: (
        "你是提纲助手。用缩进和短横线为给定文本生成层级提纲。只返回提纲。"
    ),
    AiTaskType.TITLE: (
        "你是标题生成器。为给定文本提供 3-5 个候选标题，每行一个，不要编号。"
    ),
    AiTaskType.STRUCTURE_DIAGNOSE: (
        "你是结构编辑。分析文本并报告结构问题。严格输出 JSON：\n"
        "{\"issues\": [{\"location\": 字符串, \"excerpt\": 字符串, "
        "\"problem\": 字符串, \"suggestion\": 字符串}], \"summary\": 字符串}\n"
        "只返回 JSON。"
    ),
    AiTaskType.CONSISTENCY_CHECK: (
        "你是一致性编辑。查找文本中的事实、姓名、时间线或语气矛盾。严格输出 JSON：\n"
        "{\"issues\": [{\"kind\": 字符串, \"excerpt\": 字符串, "
        "\"problem\": 字符串, \"suggestion\": 字符串}], \"summary\": 字符串}\n"
        "若没有问题，issues 为空数组，summary 明确说明。只返回 JSON。"
    ),
    AiTaskType.LIBRARY_QA: (
        "你是写作库问答助手。仅基于提供的来源附件回答问题。如答案不在来源中，"
        "明确说明。严格输出 JSON：\n"
        "{\"answer\": 字符串, \"citations\": [{\"name\": 字符串, "
        "\"excerpt\": 字符串}]}\n"
        "citations 中的 name 必须与来源附件名称完全一致。只返回 JSON。"
    ),
}


# Tasks whose output we expect to be structured JSON.
STRUCTURED_TASKS = {
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
            system += _style_guidance(is_zh)
            if request.preserve_voice:
                system += _style_voice_guidance(is_zh)
        elif request.preserve_voice:
            system += (
                " 严格保留原文的叙述声音。"
                if is_zh else
                " Strictly preserve the author's voice."
            )
        if not request.preserve_meaning:
            system += (
                " 如用户明确要求，可以调整原意。"
                if is_zh else
                " You MAY adjust the original meaning if requested."
            )

        user_parts: List[str] = []
        if request.style:
            user_parts.append(
                ("目标风格：" if is_zh else "Target style: ") + request.style
            )
        if request.intensity:
            user_parts.append(
                ("改写强度：" if is_zh else "Edit intensity: ")
                + request.intensity
            )
        if request.must_keep_terms:
            user_parts.append(
                (
                    "必须保留的词语（不要改写掉）："
                    if is_zh else
                    "Must-keep terms (do not paraphrase away): "
                )
                + ", ".join(request.must_keep_terms)
            )
        if request.forbid_terms:
            user_parts.append(
                (
                    "禁用词（不要出现）："
                    if is_zh else
                    "Forbidden terms (do not include): "
                )
                + ", ".join(request.forbid_terms)
            )
        if request.extra_instructions:
            user_parts.append(
                ("附加要求：" if is_zh else "Extra instructions: ")
                + request.extra_instructions
            )
        if request.max_output_chars:
            user_parts.append(
                (
                    f"输出尽量控制在约 {request.max_output_chars} 个字符以内。"
                    if is_zh else
                    f"Keep the output within about {request.max_output_chars} characters."
                )
            )

        if request.task_type in _REWRITE_TASKS:
            user_parts.append(_rewrite_output_contract(is_zh))
        if request.task_type is AiTaskType.POLISH:
            user_parts.append(_polish_output_guidance(request, is_zh))

        if request.attachments:
            user_parts.append(_format_attachments(request.attachments, is_zh=is_zh))

        user_parts.append(("待处理文本：\n" if is_zh else "Subject text:\n") + request.text)

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]


def _format_attachments(
    attachments: List[AiContextAttachment], *, is_zh: bool
) -> str:
    """Render attachments as a labelled source pack the model can cite by name."""
    blocks = [
        "来源附件（需要时按名称引用）："
        if is_zh else
        "Source attachments (cite by name when relevant):"
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


def _rewrite_output_contract(is_zh: bool) -> str:
    if is_zh:
        return "\n".join(
            [
                "输出要求：",
                "- 只返回一个最终改写版本。",
                "- 不要标题、不要解释、不要分点、不要附带风格解析。",
                "- 即使风格要求里写了多个作家或多个特征，也只返回一版最终结果。",
                "- 直接输出改写后的正文，不要加引号。",
            ]
        )
    return "\n".join(
        [
            "Output rules:",
            "- Return exactly one final rewritten passage.",
            "- No heading, no explanation, no bullet list, and no style analysis.",
            "- Even if the style instruction mentions multiple authors or traits, still return only one final result.",
            "- Output the rewritten prose directly, with no quotation marks.",
        ]
    )


def _polish_guidance(request: AiTaskRequest, is_zh: bool) -> str:
    intensity = (request.intensity or "").strip().lower()
    has_style = bool((request.style or "").strip())
    if is_zh:
        if intensity == "strong":
            return (
                " 这次润色允许做较大幅度的句式重组、节奏重塑和意象增强。"
                "在不改动核心事实、人物关系和场景信息的前提下，可以把原句扩写成更完整的一小段。"
            )
        if intensity == "medium":
            return (
                " 这次润色不要只做同义词替换。请做明显的句式和节奏调整；"
                "如果原文很短，且给了风格要求，可以在不添加具体新事实的前提下，"
                "把它写成更有质感的一两句或一个短段落。"
            )
        if has_style:
            return (
                " 如果给了风格要求，不要只做表面润色；即使保持克制，也要让语言纹理明显向该风格靠拢。"
            )
        return ""
    if intensity == "strong":
        return (
            " This polish pass may substantially recast sentence structure, rhythm, and imagery. "
            "As long as the core facts, relationships, and scene information remain intact, the output may expand into a fuller short paragraph."
        )
    if intensity == "medium":
        return (
            " This polish pass should do more than synonym substitution. Make noticeable changes to sentence shape and cadence; "
            "if the source is very short and a style instruction is provided, you may turn it into one or two richer sentences or a short paragraph, "
            "as long as you do not add specific new facts."
        )
    if has_style:
        return (
            " If a style instruction is present, do more than surface polish; even in a restrained pass, the prose texture should clearly move toward that style."
        )
    return ""


def _polish_output_guidance(request: AiTaskRequest, is_zh: bool) -> str:
    intensity = (request.intensity or "").strip().lower()
    has_style = bool((request.style or "").strip())
    if is_zh:
        if intensity in {"medium", "strong"} and has_style:
            return (
                "润色补充要求：如果原文很短，不要只给一个更顺一点的短句；"
                "可以把它写成更丰富的短段落，但不要凭空增加明确的新人物、事件或设定。"
            )
        if intensity in {"medium", "strong"}:
            return "润色补充要求：做明显改写，不要停留在最小幅度修辞替换。"
        return ""
    if intensity in {"medium", "strong"} and has_style:
        return (
            "Polish addendum: if the source is very short, do not return only a slightly smoother sentence; "
            "you may render it as a richer short paragraph, but do not invent explicit new characters, events, or setting facts."
        )
    if intensity in {"medium", "strong"}:
        return "Polish addendum: make a noticeable rewrite, not just the smallest possible wording swap."
    return ""
