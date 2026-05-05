"""Similarity helpers for style specimen recommendations."""
from __future__ import annotations

from collections import Counter
import re
from typing import Iterable, Sequence

from writer.domain.models.reference_passage import ReferencePassage

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "about",
    "there",
    "their",
    "they",
    "them",
    "what",
    "when",
    "where",
    "which",
    "while",
    "were",
    "was",
    "are",
    "you",
    "your",
}


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3040 <= code <= 0x309F
        or 0x30A0 <= code <= 0x30FF
        or 0xAC00 <= code <= 0xD7AF
        or 0x3400 <= code <= 0x4DBF
    )


def _contains_cjk(text: str) -> bool:
    return any(_is_cjk(ch) for ch in text)


def _terms(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if _contains_cjk(raw):
            cjk = "".join(ch for ch in raw if _is_cjk(ch))
            if len(cjk) == 1:
                out.append(cjk)
            elif len(cjk) > 1:
                out.extend(cjk[i : i + 2] for i in range(len(cjk) - 1))
                if len(cjk) <= 6:
                    out.append(cjk)
            latin = "".join(ch for ch in raw if not _is_cjk(ch))
            if len(latin) >= 3 and latin not in _STOPWORDS:
                out.append(latin)
            continue
        if len(raw) >= 3 and raw not in _STOPWORDS:
            out.append(raw)
    return out


def _weighted_overlap(query: Counter[str], text: str, weight: float) -> float:
    if not query:
        return 0.0
    hay = Counter(_terms(text))
    return weight * sum(min(count, hay.get(term, 0)) for term, count in query.items())


def _phrase_bonus(needles: Sequence[str], haystack: str, weight: float) -> float:
    hay = haystack.lower()
    bonus = 0.0
    for needle in needles:
        if len(needle) >= 4 and needle in hay:
            bonus += weight
    return bonus


def score_passage_similarity(passage: ReferencePassage, query_text: str) -> float:
    """Return a deterministic relevance score for *passage* vs. *query_text*.

    The score favours overlap in specimen body first, then the user's personal
    note, then source metadata/tags. It also gives a small exact-phrase bonus so
    stronger multi-term matches sort above one-token coincidences.
    """
    query_counter = Counter(_terms(query_text))
    if not query_counter:
        return 0.0
    query_terms = list(query_counter)
    score = 0.0
    score += _weighted_overlap(query_counter, passage.content, 3.0)
    score += _weighted_overlap(query_counter, passage.personal_note, 2.0)
    score += _weighted_overlap(
        query_counter,
        " ".join(
            [
                passage.source_title,
                passage.source_author,
                passage.tags,
                passage.usage_kind,
            ]
        ),
        1.25,
    )
    score += _phrase_bonus(query_terms, passage.content, 0.75)
    score += _phrase_bonus(query_terms, passage.personal_note, 0.5)
    # Coverage rewards passages matching several different query terms instead
    # of repeating one common token.
    candidate_terms = set(
        _terms(
            "\n".join(
                [
                    passage.content,
                    passage.personal_note,
                    passage.source_title,
                    passage.source_author,
                    passage.tags,
                    passage.usage_kind,
                ]
            )
        )
    )
    distinct_hits = len(set(query_counter) & candidate_terms)
    score += distinct_hits / max(1, len(query_counter))
    return score


def rank_similar_passages(
    passages: Iterable[ReferencePassage], query_text: str, *, limit: int = 6
) -> list[ReferencePassage]:
    scored = [
        (score_passage_similarity(passage, query_text), idx, passage)
        for idx, passage in enumerate(passages)
    ]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1], item[2].source_title.lower()))
    return [passage for _score, _idx, passage in scored[:limit]]
