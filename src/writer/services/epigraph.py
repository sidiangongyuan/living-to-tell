"""Pure-text epigraph detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re


MAX_SCAN_LINES = 8
MAX_QUOTE_LINES = 4
MAX_TOTAL_LINES = 5
MAX_QUOTE_CHARS = 240
MAX_ATTRIBUTION_CHARS = 120

_DASH_PREFIX_RE = re.compile(r"^\s*[—-]{1,2}\s*")
_LEADING_QUOTES_RE = re.compile(r"^[\"'“”‘’「」『』《》〈〉‹›«»]+")
_TRAILING_QUOTES_RE = re.compile(r"[\"'“”‘’「」『』《》〈〉‹›«»]+$")
_BOOK_RE = re.compile(r"《[^《》\n]{1,40}》")
_ATTR_LINE_RE = re.compile(r"^\s*(?:[—-]{1,2}\s*)?(?P<content>.+?)\s*$")
_SAME_LINE_SPLIT_RE = re.compile(
    r"^(?P<quote>.+?)(?:\s{2,}|[ \t]+[—-]{1,2}[ \t]+)(?P<attr>.+)$"
)
_SAME_LINE_DASH_SPLIT_RE = re.compile(
    r"^(?P<quote>.+?)(?P<sep>[—-]{1,2}\s*)(?P<attr>.+)$"
)
_SAME_LINE_PUNCT_SPLIT_RE = re.compile(
    r"^(?P<quote>.+[。！？!?…][\"'”’」』》〉»]*)\s+(?P<attr>.+)$"
)
_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:chapter|section|part|prologue|epilogue|第[一二三四五六七八九十百千0-9]+[章节回部卷篇])\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Epigraph:
    quote_text: str
    source_text: str
    raw_text: str
    end_offset: int

    @property
    def quote(self) -> str:
        return self.quote_text

    @property
    def attribution(self) -> str:
        return self.source_text

    @property
    def line_count(self) -> int:
        return _count_lines(self.raw_text)

    @property
    def source_span(self) -> tuple[int, int]:
        return (0, self.line_count)


def detect_epigraph(text: str) -> Epigraph | None:
    """Detect an opening epigraph from the first few lines of plain text."""
    if not text or not text.strip():
        return None

    scanned_lines = 0
    current_offset = 0
    line_ends: list[int] = []
    line_texts: list[str] = []

    while scanned_lines < MAX_SCAN_LINES and current_offset < len(text):
        newline_idx = text.find("\n", current_offset)
        if newline_idx == -1:
            line_end = len(text)
            next_offset = len(text)
        else:
            line_end = newline_idx
            next_offset = newline_idx + 1
        raw_line = text[current_offset:line_end]
        if raw_line.endswith("\r"):
            raw_line = raw_line[:-1]
        line_texts.append(raw_line)
        line_ends.append(next_offset)
        scanned_lines += 1
        if newline_idx == -1:
            break
        current_offset = next_offset

    scan_limit = len(line_texts)
    for attr_idx in range(scan_limit):
        candidate = _build_candidate(text, line_texts, line_ends, attr_idx)
        if candidate is not None:
            return candidate
    return None


def strip_epigraph(text: str) -> str:
    """Remove the leading epigraph block, if present, preserving the body."""
    epigraph = detect_epigraph(text)
    if epigraph is None:
        return text
    return text[epigraph.end_offset :].lstrip()


def _build_candidate(
    text: str,
    lines: list[str],
    line_ends: list[int],
    attr_idx: int,
) -> Epigraph | None:
    attr_line = lines[attr_idx]
    attr = _parse_attribution(attr_line)
    if attr is not None:
        quote_lines = lines[:attr_idx]
        candidate = _make_epigraph(
            text=text,
            quote_lines=quote_lines,
            attribution=attr,
            block_start=0,
            block_end=line_ends[attr_idx],
        )
        if candidate is not None:
            return candidate

    same_line = _parse_same_line(lines[attr_idx])
    if same_line is None or attr_idx > 0:
        return None
    quote_text, same_attr = same_line
    return _make_epigraph(
        text=text,
        quote_lines=[quote_text],
        attribution=same_attr,
        block_start=0,
        block_end=line_ends[attr_idx],
    )


def _make_epigraph(
    *,
    text: str,
    quote_lines: list[str],
    attribution: str,
    block_start: int,
    block_end: int,
) -> Epigraph | None:
    trimmed_quote_lines = _trim_blank_edges(quote_lines)
    if not trimmed_quote_lines:
        return None
    raw_text = text[block_start:block_end]
    line_count = _count_lines(raw_text)
    if len(trimmed_quote_lines) > MAX_QUOTE_LINES:
        return None
    if line_count > MAX_TOTAL_LINES:
        return None

    quote = "\n".join(line.rstrip() for line in trimmed_quote_lines).strip()
    source_text = attribution.strip()
    if not quote or not source_text:
        return None
    if len(quote) > MAX_QUOTE_CHARS or len(source_text) > MAX_ATTRIBUTION_CHARS:
        return None
    if not _looks_like_attribution(source_text):
        return None
    if _looks_like_body_opening(quote):
        return None

    return Epigraph(
        quote_text=quote,
        source_text=source_text,
        raw_text=raw_text,
        end_offset=block_end,
    )


def _parse_same_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    match = _SAME_LINE_SPLIT_RE.match(stripped)
    if not match:
        match = _SAME_LINE_DASH_SPLIT_RE.match(stripped)
    if not match:
        match = _SAME_LINE_PUNCT_SPLIT_RE.match(stripped)
    if not match:
        return None
    quote = match.group("quote").strip()
    attr = match.group("attr").strip()
    if not quote or not attr:
        return None
    if not _looks_like_attribution(attr):
        return None
    return quote, _normalise_attribution(attr)


def _parse_attribution(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    match = _ATTR_LINE_RE.match(stripped)
    if not match:
        return None
    content = match.group("content").strip()
    if not _looks_like_attribution(content):
        return None
    return _normalise_attribution(content)


def _looks_like_attribution(text: str) -> bool:
    if not text or "\n" in text:
        return False
    compact = text.strip()
    if len(compact) < 2 or len(compact) > MAX_ATTRIBUTION_CHARS:
        return False
    if compact.endswith(("。", "！", "？", "!", "?")):
        return False
    if _BOOK_RE.search(compact):
        return True
    parts = [part.strip() for part in compact.split("，") if part.strip()]
    if len(parts) != 2:
        return False
    return any(_BOOK_RE.search(part) for part in parts)


def _normalise_attribution(text: str) -> str:
    compact = _DASH_PREFIX_RE.sub("", text.strip())
    return re.sub(r"\s+", " ", compact).strip()


def _looks_like_body_opening(quote: str) -> bool:
    stripped = quote.strip()
    if not stripped:
        return True
    single_line = "\n" not in stripped
    compact = stripped.replace("\n", " ").strip()
    plain = _strip_wrapping_quotes(compact)
    lines = [_strip_wrapping_quotes(line.strip()) for line in stripped.splitlines() if line.strip()]
    if not plain:
        return True
    if _SECTION_HEADING_RE.match(plain):
        return True
    if single_line and len(plain) > 90 and "。" not in plain and "." not in plain:
        return True
    if (
        len(lines) >= 2
        and all(len(line) >= 12 for line in lines)
        and sum(line.endswith(("。", "！", "？", ".", "!", "?")) for line in lines) >= 2
    ):
        return True
    if plain.endswith(("：", ":")):
        return True
    if plain.startswith(
        (
            "我",
            "我们",
            "那天",
            "后来",
            "于是",
            "首先",
            "今天",
            "清晨",
            "凌晨",
            "夜里",
            "雨",
            "风",
            "门外",
        )
    ) and len(plain) > 20:
        return True
    if "，" not in plain and "。" not in plain and len(plain.split()) > 18:
        return True
    return False


def _trim_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _strip_wrapping_quotes(text: str) -> str:
    stripped = _LEADING_QUOTES_RE.sub("", text)
    stripped = _TRAILING_QUOTES_RE.sub("", stripped)
    return stripped.strip()


def _count_lines(text: str) -> int:
    return len(text.splitlines()) if text else 0
