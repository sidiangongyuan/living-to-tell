"""Hand-written application container.

Centralises construction of long-lived objects (database connection,
repositories, settings facade). Intentionally simple — no DI framework, no
service locator. Wiring code lives here so the rest of the app stays unaware
of how things are built.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from writer.app.settings import Settings
from writer.services.ai.gemini_cli_provider import GeminiCliProvider
from writer.services.ai.gemini_provider import GeminiProvider
from writer.services.ai.opencode_cli_provider import OpenCodeCliProvider
from writer.services.ai.openai_provider import OpenAiProvider
from writer.services.ai.prompt_builder import PromptBuilder
from writer.services.ai.rewrite_service import RewriteService
from writer.services.ai.task_prompt_builder import TaskPromptBuilder
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import AiContextAttachment
from writer.services.ai.thread_service import AiThreadService
from writer.services.export import CollectionExportService, MarkdownExporter, TextExporter
from writer.services.legacy_work_import import LegacyWorkImportService
from writer.services.export.work_exporter import WorkExportService
from writer.services.search_service import SearchService
from writer.services.version_history_service import VersionHistoryService
from writer.services.work_service import WorkService
from writer.storage.database import open_and_initialize
from writer.storage.repositories.ai_card_repository import AiCardRepository
from writer.storage.repositories.ai_thread_repository import AiThreadRepository
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.collection_outline_repository import (
    CollectionOutlineRepository,
)
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.entry_writing_note_repository import (
    EntryWritingNoteRepository,
)
from writer.storage.repositories.motif_repository import MotifRepository
from writer.storage.repositories.project_repository import ProjectRepository
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.storage.repositories.settings_repository import SettingsRepository
from writer.storage.repositories.version_repository import VersionRepository
from writer.storage.repositories.work_fragment_ref_repository import (
    WorkFragmentRefRepository,
)
from writer.storage.repositories.work_repository import WorkRepository
from writer.storage.repositories.work_section_repository import (
    WorkSectionRepository,
)
from writer.storage.repositories.work_version_repository import (
    WorkVersionRepository,
)


@dataclass
class AppContainer:
    """Holds the wired dependencies for the application."""

    connection: sqlite3.Connection
    settings_repository: SettingsRepository
    settings: Settings
    entry_repository: EntryRepository
    entry_writing_note_repository: EntryWritingNoteRepository
    motif_repository: MotifRepository
    version_repository: VersionRepository
    reference_repository: ReferenceRepository
    project_repository: ProjectRepository
    chapter_repository: ChapterRepository
    search_service: SearchService
    prompt_builder: PromptBuilder
    rewrite_service: RewriteService
    markdown_exporter: MarkdownExporter
    text_exporter: TextExporter
    version_history_service: VersionHistoryService
    work_repository: WorkRepository
    work_section_repository: WorkSectionRepository
    collection_repository: CollectionRepository
    collection_outline_repository: CollectionOutlineRepository
    work_fragment_ref_repository: WorkFragmentRefRepository
    work_version_repository: WorkVersionRepository
    work_service: WorkService
    work_export_service: WorkExportService
    collection_export_service: CollectionExportService
    legacy_work_import_service: LegacyWorkImportService
    # M10A: AI workspace
    ai_thread_repository: AiThreadRepository
    ai_card_repository: AiCardRepository
    ai_task_service: AiTaskService
    ai_thread_service: AiThreadService

    def close(self) -> None:
        try:
            self.connection.close()
        except sqlite3.Error:
            pass


def build_container(db_path: Optional[Path] = None) -> AppContainer:
    """Create the application's services and repositories."""
    conn = open_and_initialize(db_path)
    settings_repo = SettingsRepository(conn)
    settings = Settings(settings_repo)

    # One-shot opportunistic migration from env:OPENAI_API_KEY → codex for
    # users who already run Codex locally. See app/codex_auth_migration.py
    # for the exact gating rules. Failures must not block startup.
    try:
        from writer.app.codex_auth_migration import maybe_migrate_to_codex_auth

        maybe_migrate_to_codex_auth(settings)
    except Exception:  # noqa: BLE001
        pass

    entry_repo = EntryRepository(conn)
    entry_note_repo = EntryWritingNoteRepository(conn)
    motif_repo = MotifRepository(conn)
    version_repo = VersionRepository(conn)
    reference_repo = ReferenceRepository(conn)
    project_repo = ProjectRepository(conn)
    chapter_repo = ChapterRepository(conn)
    search_service = SearchService(conn)
    prompt_builder = PromptBuilder()

    def _provider_factory():
        config = settings.load_ai_config()
        if config.provider_key() == "opencode" or config.uses_opencode_auth():
            return OpenCodeCliProvider(config, prompt_builder)
        if config.provider_key() == "gemini_cli":
            return GeminiCliProvider(config, prompt_builder)
        if config.provider_key() == "gemini" or config.uses_gemini_auth():
            return GeminiProvider(config, prompt_builder)
        return OpenAiProvider(config, prompt_builder)

    rewrite_service = RewriteService(entry_repo, version_repo, _provider_factory)
    markdown_exporter = MarkdownExporter(entry_repo, chapter_repo)
    text_exporter = TextExporter(entry_repo, chapter_repo)
    version_history_service = VersionHistoryService(entry_repo, version_repo)

    work_repo = WorkRepository(conn)
    section_repo = WorkSectionRepository(conn)
    collection_repo = CollectionRepository(conn)
    collection_outline_repo = CollectionOutlineRepository(conn)
    work_ref_repo = WorkFragmentRefRepository(conn)
    work_version_repo = WorkVersionRepository(conn)
    work_service = WorkService(
        conn,
        work_repo,
        section_repo,
        work_ref_repo,
        work_version_repo,
        entry_repo,
    )
    work_export_service = WorkExportService(
        work_repo, section_repo, collection_repo
    )
    collection_export_service = CollectionExportService(collection_repo)
    legacy_work_import_service = LegacyWorkImportService(
        conn,
        settings_repo,
        entry_repo,
        collection_repo,
    )

    # ---- M10A: AI workspace -----------------------------------------
    ai_thread_repo = AiThreadRepository(conn)
    # Cards (style/character/scene) and saved task templates: schema
    # and repository are wired so future milestones can land the UI
    # without a migration. There is intentionally no card or template
    # entry point in the M10A panel — that surface is deferred.
    ai_card_repo = AiCardRepository(conn)
    task_prompt_builder = TaskPromptBuilder()

    def _library_search(query: str, limit: int):
        # Provide library QA with up to ``limit`` candidate fragments
        # (and a short body excerpt) as source attachments. Works /
        # sections are also fair game; we keep the v1 implementation
        # simple by routing through the existing entry FTS service.
        results = []
        try:
            hits = search_service.search(query, limit=limit)
        except Exception:  # noqa: BLE001 — searching must not break AI flow
            hits = []
        for entry in hits[:limit]:
            body = entry.body or ""
            excerpt = body[:1200]
            results.append(
                AiContextAttachment(
                    kind="fragment",
                    ref_id=entry.id,
                    name=(entry.title or "(untitled fragment)") + f" [{entry.id[:8]}]",
                    body=excerpt,
                )
            )
        return results

    ai_task_service = AiTaskService(
        _provider_factory,
        settings,
        prompt_builder=task_prompt_builder,
        library_search=_library_search,
    )
    ai_thread_service = AiThreadService(
        ai_thread_repo, _provider_factory, ai_task_service
    )

    return AppContainer(
        connection=conn,
        settings_repository=settings_repo,
        settings=settings,
        entry_repository=entry_repo,
        entry_writing_note_repository=entry_note_repo,
        motif_repository=motif_repo,
        version_repository=version_repo,
        reference_repository=reference_repo,
        project_repository=project_repo,
        chapter_repository=chapter_repo,
        search_service=search_service,
        prompt_builder=prompt_builder,
        rewrite_service=rewrite_service,
        markdown_exporter=markdown_exporter,
        text_exporter=text_exporter,
        version_history_service=version_history_service,
        work_repository=work_repo,
        work_section_repository=section_repo,
        collection_repository=collection_repo,
        collection_outline_repository=collection_outline_repo,
        work_fragment_ref_repository=work_ref_repo,
        work_version_repository=work_version_repo,
        work_service=work_service,
        work_export_service=work_export_service,
        collection_export_service=collection_export_service,
        legacy_work_import_service=legacy_work_import_service,
        ai_thread_repository=ai_thread_repo,
        ai_card_repository=ai_card_repo,
        ai_task_service=ai_task_service,
        ai_thread_service=ai_thread_service,
    )
