from writer.services.export.collection_exporter import CollectionExportService
from writer.storage.database import open_and_initialize
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository


def test_collection_markdown_exports_ordered_articles_and_epigraph_once(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)
    first = entries.create(
        title="First",
        body="“一句话。” ——《书》 作者\n\n正文开始。",
    )
    second = entries.create(title="Second", body="第二篇正文。")
    collection = collections.create("Book", description="Preface")
    collections.add_entry(collection.id, second.id)
    collections.add_entry(collection.id, first.id)

    md = CollectionExportService(collections).export_collection_md(collection.id)

    assert md.index("## Second") < md.index("## First")
    assert "# Book" in md
    assert "Preface" in md
    assert md.count("正文开始。") == 1
    assert md.count("“一句话。”") == 1


def test_collection_txt_exports_description_and_contents(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)
    entry = entries.create(title="Essay", body="body")
    collection = collections.create("Anthology", description="Intro")
    collections.add_entry(collection.id, entry.id)

    text = CollectionExportService(collections).export_collection_txt(collection.id)

    assert "Anthology" in text
    assert "Intro" in text
    assert "Contents" in text
    assert "Essay" in text
    assert "body" in text
