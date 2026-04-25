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
from writer.services.ai.openai_provider import OpenAiProvider
from writer.services.ai.prompt_builder import PromptBuilder
from writer.services.ai.rewrite_service import RewriteService
from writer.services.export import MarkdownExporter, TextExporter
from writer.services.export.work_exporter import WorkExportService
from writer.services.search_service import SearchService
from writer.services.version_history_service import VersionHistoryService
from writer.services.work_service import WorkService
from writer.storage.database import open_and_initialize
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
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
    work_fragment_ref_repository: WorkFragmentRefRepository
    work_version_repository: WorkVersionRepository
    work_service: WorkService
    work_export_service: WorkExportService

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
    version_repo = VersionRepository(conn)
    reference_repo = ReferenceRepository(conn)
    project_repo = ProjectRepository(conn)
    chapter_repo = ChapterRepository(conn)
    search_service = SearchService(conn)
    prompt_builder = PromptBuilder()

    def _provider_factory():
        return OpenAiProvider(settings.load_ai_config(), prompt_builder)

    rewrite_service = RewriteService(entry_repo, version_repo, _provider_factory)
    markdown_exporter = MarkdownExporter(entry_repo, chapter_repo)
    text_exporter = TextExporter(entry_repo, chapter_repo)
    version_history_service = VersionHistoryService(entry_repo, version_repo)

    work_repo = WorkRepository(conn)
    section_repo = WorkSectionRepository(conn)
    collection_repo = CollectionRepository(conn)
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

    return AppContainer(
        connection=conn,
        settings_repository=settings_repo,
        settings=settings,
        entry_repository=entry_repo,
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
        work_fragment_ref_repository=work_ref_repo,
        work_version_repository=work_version_repo,
        work_service=work_service,
        work_export_service=work_export_service,
    )
