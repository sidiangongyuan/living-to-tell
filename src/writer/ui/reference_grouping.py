"""UI-only grouping helpers for the specimen picker and reference library."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from writer.domain.models.reference_passage import ReferencePassage
from writer.ui.i18n import TR


GROUP_MODE_SOURCE = "source"
GROUP_MODE_USAGE = "usage"
GROUP_MODE_TAG = "tag"
GROUP_MODE_SOURCE_USAGE = "source_usage"
GROUP_MODE_USAGE_TAG = "usage_tag"
GROUP_MODE_RECENT = "recent"

GROUP_MODES: tuple[str, ...] = (
    GROUP_MODE_SOURCE,
    GROUP_MODE_USAGE,
    GROUP_MODE_TAG,
    GROUP_MODE_SOURCE_USAGE,
    GROUP_MODE_USAGE_TAG,
    GROUP_MODE_RECENT,
)

DEFAULT_REFERENCE_LIBRARY_GROUP_MODE = GROUP_MODE_SOURCE
DEFAULT_SPECIMEN_PICKER_GROUP_MODE = GROUP_MODE_SOURCE_USAGE

ALL_GROUP_KEY = "__all__"
NON_PASSAGE_ITEM = "__none__"
UNLABELED_SOURCE_KEY = "__unlabeled_source__"
UNLABELED_TAG_KEY = "__unlabeled_tag__"
UNKNOWN_DATE_KEY = "__unknown_date__"

_USAGE_LABEL_KEYS = {
    "style": "reflib.usage_kind_style",
    "imagery": "reflib.usage_kind_imagery",
    "structure": "reflib.usage_kind_structure",
    "rhetoric": "reflib.usage_kind_rhetoric",
    "diction": "reflib.usage_kind_diction",
    "technique": "reflib.usage_kind_technique",
    "character": "reflib.usage_kind_character",
    "setting": "reflib.usage_kind_setting",
    "psychology": "reflib.usage_kind_psychology",
    "philosophy": "reflib.usage_kind_philosophy",
    "reflection": "reflib.usage_kind_reflection",
    "other": "reflib.usage_kind_other",
}

_GROUP_MODE_LABEL_KEYS = {
    GROUP_MODE_SOURCE: "reflib.group_mode_source",
    GROUP_MODE_USAGE: "reflib.group_mode_usage",
    GROUP_MODE_TAG: "reflib.group_mode_tag",
    GROUP_MODE_SOURCE_USAGE: "reflib.group_mode_source_usage",
    GROUP_MODE_USAGE_TAG: "reflib.group_mode_usage_tag",
    GROUP_MODE_RECENT: "reflib.group_mode_recent",
}


@dataclass(frozen=True)
class PassageSection:
    key: str
    title: str
    passages: tuple[ReferencePassage, ...]


@dataclass(frozen=True)
class PassageGroup:
    key: str
    title: str
    subtitle: str
    sections: tuple[PassageSection, ...]
    count: int

    def contains(self, passage_id: str) -> bool:
        return any(
            passage.id == passage_id
            for section in self.sections
            for passage in section.passages
        )


@dataclass
class _SectionBuilder:
    key: str
    title: str
    passages: list[ReferencePassage] = field(default_factory=list)


@dataclass
class _GroupBuilder:
    key: str
    title: str
    subtitle: str = ""
    sections: dict[str, _SectionBuilder] = field(default_factory=dict)


def group_mode_label(mode: str) -> str:
    return TR(_GROUP_MODE_LABEL_KEYS.get(mode, "reflib.group_mode_source"))


def group_mode_options() -> list[tuple[str, str]]:
    return [(mode, group_mode_label(mode)) for mode in GROUP_MODES]


def normalize_group_mode(
    value: Optional[str],
    *,
    default: str = DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
) -> str:
    raw = (value or "").strip().lower()
    return raw if raw in GROUP_MODES else default


def usage_kind_label(value: str) -> str:
    return TR(_USAGE_LABEL_KEYS.get(value, "reflib.usage_kind_style"))


def split_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in (tags or "").split(",") if tag.strip()]


def source_group_title(source_title: str) -> str:
    title = (source_title or "").strip()
    return title or TR("specimen.group_unlabeled_source")


def tag_group_title(tag: str) -> str:
    value = (tag or "").strip()
    return value or TR("specimen.group_unlabeled_tag")


def compact_text(value: str, *, limit: int = 160) -> str:
    compact = " ".join((value or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "…"


def display_date_label(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if len(raw) >= 10:
        return raw[:10]
    return TR("reflib.group_recent_unknown")


def find_group_key_for_passage(
    groups: Iterable[PassageGroup], passage_id: Optional[str]
) -> Optional[str]:
    if not passage_id:
        return None
    for group in groups:
        if group.contains(passage_id):
            return group.key
    return None


def group_reference_passages(
    passages: Iterable[ReferencePassage],
    mode: str,
) -> list[PassageGroup]:
    normalized_mode = normalize_group_mode(mode)
    group_builders: dict[str, _GroupBuilder] = {}

    for passage in passages:
        for top_key, top_title, top_subtitle, section_key, section_title in _assignments_for(
            passage,
            normalized_mode,
        ):
            group = group_builders.get(top_key)
            if group is None:
                group = _GroupBuilder(
                    key=top_key,
                    title=top_title,
                    subtitle=top_subtitle,
                )
                group_builders[top_key] = group
            else:
                group.subtitle = _merge_subtitle(group.subtitle, top_subtitle)
            section = group.sections.get(section_key)
            if section is None:
                section = _SectionBuilder(key=section_key, title=section_title)
                group.sections[section_key] = section
            section.passages.append(passage)

    out: list[PassageGroup] = []
    for group in group_builders.values():
        sections = tuple(
            PassageSection(
                key=section.key,
                title=section.title,
                passages=tuple(section.passages),
            )
            for section in group.sections.values()
        )
        out.append(
            PassageGroup(
                key=group.key,
                title=group.title,
                subtitle=group.subtitle,
                sections=sections,
                count=sum(len(section.passages) for section in sections),
            )
        )
    return out


def _assignments_for(
    passage: ReferencePassage,
    mode: str,
) -> list[tuple[str, str, str, str, str]]:
    if mode == GROUP_MODE_SOURCE:
        key, title, subtitle = _source_group_tuple(passage)
        return [(key, title, subtitle, "__items__", "",)]
    if mode == GROUP_MODE_USAGE:
        title = usage_kind_label(passage.usage_kind)
        return [(passage.usage_kind, title, "", "__items__", "",)]
    if mode == GROUP_MODE_TAG:
        return [
            (tag_key, tag_title, "", "__items__", "")
            for tag_key, tag_title in _tag_group_tuples(passage)
        ]
    if mode == GROUP_MODE_SOURCE_USAGE:
        key, title, subtitle = _source_group_tuple(passage)
        section_title = usage_kind_label(passage.usage_kind)
        return [(key, title, subtitle, passage.usage_kind, section_title)]
    if mode == GROUP_MODE_USAGE_TAG:
        top_title = usage_kind_label(passage.usage_kind)
        return [
            (passage.usage_kind, top_title, "", tag_key, tag_title)
            for tag_key, tag_title in _tag_group_tuples(passage)
        ]
    date_key = _created_date_key(passage.created_at)
    return [(date_key, display_date_label(passage.created_at), "", "__items__", "")]


def _source_group_tuple(passage: ReferencePassage) -> tuple[str, str, str]:
    title = (passage.source_title or "").strip()
    author = (passage.source_author or "").strip()
    if not title:
        return (UNLABELED_SOURCE_KEY, TR("specimen.group_unlabeled_source"), "")
    return (title.casefold(), title, author)


def _tag_group_tuples(passage: ReferencePassage) -> list[tuple[str, str]]:
    tags = split_tags(passage.tags)
    if not tags:
        return [(UNLABELED_TAG_KEY, TR("specimen.group_unlabeled_tag"))]
    return [(tag.casefold(), tag) for tag in tags]


def _created_date_key(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if len(raw) >= 10:
        return raw[:10]
    return UNKNOWN_DATE_KEY


def _merge_subtitle(current: str, incoming: str) -> str:
    left = (current or "").strip()
    right = (incoming or "").strip()
    if not left:
        return right
    if not right or right == left:
        return left
    return ""
