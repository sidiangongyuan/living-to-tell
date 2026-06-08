"""Article collection exporters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from writer.domain.models.collection import Collection
from writer.domain.models.entry import Entry
from writer.services.epigraph import detect_epigraph, strip_epigraph
from writer.storage.repositories.collection_repository import CollectionRepository


@dataclass
class _ArticleBundle:
    entry: Entry
    word_count: int


class CollectionExportService:
    def __init__(self, collection_repo: CollectionRepository) -> None:
        self._collections = collection_repo

    def export_collection_txt(self, collection_id: str) -> str:
        collection, bundles = self._load_collection(collection_id)
        parts: List[str] = []
        title = collection.name or "Untitled collection"
        parts.append(f"{title}\n{'=' * max(1, len(title))}")
        if collection.description.strip():
            parts.append(collection.description.strip())
        if bundles:
            toc = ["Contents", "--------"]
            for index, bundle in enumerate(bundles, start=1):
                article_title = bundle.entry.title or "Untitled article"
                toc.append(f"{index}. {article_title}  [{bundle.word_count} words]")
            parts.append("\n".join(toc))
        for bundle in bundles:
            parts.append(_render_article_text(bundle.entry))
        return "\n\n".join(parts).rstrip() + "\n"

    def export_collection_md(self, collection_id: str) -> str:
        collection, bundles = self._load_collection(collection_id)
        lines: List[str] = [f"# {collection.name or 'Untitled collection'}"]
        if collection.description.strip():
            lines.append("")
            lines.append(collection.description.strip())
        if bundles:
            lines.append("")
            lines.append("## Contents")
            for index, bundle in enumerate(bundles, start=1):
                article_title = bundle.entry.title or "Untitled article"
                lines.append(f"{index}. {article_title}  _({bundle.word_count} words)_")
        for bundle in bundles:
            lines.append("")
            lines.append(_render_article_markdown(bundle.entry, heading_level=2))
        return "\n".join(lines).rstrip() + "\n"

    def export_collection_docx(self, collection_id: str, output_path: str) -> str:
        collection, bundles = self._load_collection(collection_id)
        document = _new_document()
        document.add_heading(collection.name or "Untitled collection", level=0)
        if collection.description.strip():
            document.add_paragraph(collection.description.strip())
        if bundles:
            document.add_heading("Contents", level=1)
            for index, bundle in enumerate(bundles, start=1):
                title = bundle.entry.title or "Untitled article"
                document.add_paragraph(f"{index}. {title}  ({bundle.word_count} words)")
        for bundle in bundles:
            _write_article_docx(document, bundle.entry, heading_level=1)
        document.save(output_path)
        return output_path

    def _load_collection(self, collection_id: str) -> tuple[Collection, List[_ArticleBundle]]:
        collection = self._collections.get(collection_id)
        if collection is None:
            raise ValueError(f"unknown collection: {collection_id!r}")
        bundles = [
            _ArticleBundle(entry=entry, word_count=_word_count(entry.body or ""))
            for entry in self._collections.list_entries(collection_id)
        ]
        return collection, bundles


def _render_article_text(entry: Entry) -> str:
    title = entry.title or "Untitled article"
    body = (entry.body or "").strip()
    if not body:
        return f"{title}\n{'-' * max(1, len(title))}"
    return f"{title}\n{'-' * max(1, len(title))}\n\n{body}".rstrip()


def _render_article_markdown(entry: Entry, *, heading_level: int) -> str:
    level = max(1, min(5, heading_level))
    title = entry.title or "Untitled article"
    body = (entry.body or "").strip()
    lines: List[str] = [f"{'#' * level} {title}"]
    if not body:
        return "\n".join(lines)
    epigraph = detect_epigraph(body)
    rendered_body = strip_epigraph(body).rstrip() if epigraph is not None else body
    lines.append("")
    if epigraph is not None:
        lines.extend(_render_epigraph_markdown_lines(epigraph))
        if rendered_body:
            lines.append("")
    if rendered_body:
        lines.append(rendered_body)
    return "\n".join(lines).rstrip()


def _write_article_docx(document, entry: Entry, *, heading_level: int) -> None:
    document.add_heading(entry.title or "Untitled article", level=heading_level)
    body = (entry.body or "").strip()
    if not body:
        return
    epigraph = detect_epigraph(body)
    rendered_body = strip_epigraph(body).rstrip() if epigraph is not None else body
    if epigraph is not None:
        _write_epigraph_docx(document, epigraph)
    if rendered_body:
        for para in rendered_body.split("\n\n"):
            document.add_paragraph(para)


def _word_count(body: str) -> int:
    if not body:
        return 0
    total = 0
    buf: list[str] = []
    for ch in body:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            if buf:
                if "".join(buf).strip():
                    total += 1
                buf = []
            total += 1
        else:
            buf.append(ch)
    if buf:
        total += len([token for token in "".join(buf).split() if token.strip()])
    return total


def _new_document():
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:  # pragma: no cover - env-specific
        raise RuntimeError(
            "python-docx is required for DOCX export. Install it with: pip install python-docx"
        ) from exc
    return Document()


def _render_epigraph_markdown_lines(epigraph) -> list[str]:
    lines = [f"> {line}" if line else ">" for line in epigraph.quote.splitlines()]
    lines.append(">")
    lines.append(f"> -- {epigraph.attribution}")
    return lines


def _write_epigraph_docx(document, epigraph) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH  # type: ignore
    from docx.shared import Inches, Pt  # type: ignore

    for line in epigraph.quote.splitlines():
        para = document.add_paragraph()
        para.paragraph_format.left_indent = Inches(0.35)
        para.paragraph_format.right_indent = Inches(0.55)
        para.paragraph_format.space_after = Pt(0)
        run = para.add_run(line)
        run.italic = True

    attr_para = document.add_paragraph()
    attr_para.paragraph_format.right_indent = Inches(0.55)
    attr_para.paragraph_format.space_after = Pt(8)
    attr_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    attr_para.add_run(epigraph.attribution)
