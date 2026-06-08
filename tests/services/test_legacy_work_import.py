from writer.services.legacy_work_import import LegacyWorkImportService
from writer.storage.database import open_and_initialize
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.settings_repository import SettingsRepository
from writer.storage.repositories.work_repository import WorkRepository
from writer.storage.repositories.work_section_repository import WorkSectionRepository


def test_legacy_work_import_turns_sections_into_articles_and_collection(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    settings = SettingsRepository(conn)
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)
    works = WorkRepository(conn)
    sections = WorkSectionRepository(conn)
    work = works.create(title="Old Work", summary="Old summary", tags=["tag"])
    sections.create(work.id, content="第一章\n正文")
    sections.create(work.id, content="第二章\n正文")

    service = LegacyWorkImportService(conn, settings, entries, collections)
    summary = service.import_once()

    assert summary.entries_created == 2
    assert summary.collections_created == 1
    collection = collections.list_all()[0]
    assert collection.name == "Old Work"
    assert collection.description == "Old summary"
    imported = collections.list_entries(collection.id)
    assert [entry.title for entry in imported] == ["第一章", "第二章"]
    assert imported[0].tags == ["tag"]
    assert service.needs_import() is False


def test_legacy_work_import_is_idempotent(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    settings = SettingsRepository(conn)
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)
    works = WorkRepository(conn)
    sections = WorkSectionRepository(conn)
    work = works.create(title="Old Work")
    sections.create(work.id, content="body")

    service = LegacyWorkImportService(conn, settings, entries, collections)
    service.import_once()
    second = service.import_once()

    assert second.entries_created == 0
    assert entries.count() == 1
    assert collections.count() == 1
