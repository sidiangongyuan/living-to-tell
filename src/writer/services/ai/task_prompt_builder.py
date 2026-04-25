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
        system = self.system_prompt(request.task_type)
        if request.preserve_voice:
            system += " Strictly preserve the author's voice."
        if not request.preserve_meaning:
            system += " You MAY adjust the original meaning if requested."

        user_parts: List[str] = []
        if request.style:
            user_parts.append(f"Target style: {request.style}")
        if request.intensity:
            user_parts.append(f"Edit intensity: {request.intensity}")
        if request.must_keep_terms:
            user_parts.append(
                "Must-keep terms (do not paraphrase away): "
                + ", ".join(request.must_keep_terms)
            )
        if request.forbid_terms:
            user_parts.append(
                "Forbidden terms (do not include): "
                + ", ".join(request.forbid_terms)
            )
        if request.extra_instructions:
            user_parts.append("Extra instructions: " + request.extra_instructions)
        if request.max_output_chars:
            user_parts.append(
                f"Keep the output within about {request.max_output_chars} characters."
            )

        if request.attachments:
            user_parts.append(_format_attachments(request.attachments))

        user_parts.append("Subject text:\n" + request.text)

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]


def _format_attachments(attachments: List[AiContextAttachment]) -> str:
    """Render attachments as a labelled source pack the model can cite by name."""
    blocks = ["Source attachments (cite by name when relevant):"]
    for att in attachments:
        header = f"[{att.kind}] {att.name}"
        body = att.body.strip()
        if not body:
            continue
        blocks.append(f"--- {header} ---\n{body}")
    return "\n\n".join(blocks)
