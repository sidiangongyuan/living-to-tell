from writer.storage.database import open_and_initialize
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository


def test_collection_can_contain_articles_in_order(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)

    first = entries.create(title="A", body="alpha")
    second = entries.create(title="B", body="beta")
    collection = collections.create("Book")

    collections.add_entry(collection.id, first.id)
    collections.add_entry(collection.id, second.id)
    collections.reorder_entries(collection.id, [second.id, first.id])

    assert [entry.id for entry in collections.list_entries(collection.id)] == [
        second.id,
        first.id,
    ]
    assert collections.list_collections_containing_entry(first.id)[0].id == collection.id


def test_entry_can_belong_to_multiple_collections(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)

    entry = entries.create(title="Essay", body="body")
    one = collections.create("One")
    two = collections.create("Two")

    collections.add_entry(one.id, entry.id)
    collections.add_entry(two.id, entry.id)

    assert {c.id for c in collections.list_collections_containing_entry(entry.id)} == {
        one.id,
        two.id,
    }


def test_collection_project_type_is_saved_and_validated(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    collections = CollectionRepository(conn)

    collection = collections.create("Novel", project_type="novel")

    assert collection.project_type == "novel"
    assert collections.update_project_type(collection.id, "essay").project_type == "essay"

    try:
        collections.update_project_type(collection.id, "bad")
    except ValueError as exc:
        assert "Unsupported collection project type" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid project type should fail")


def test_deleting_entry_removes_collection_membership(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    collections = CollectionRepository(conn)

    entry = entries.create(title="Essay", body="body")
    collection = collections.create("Book")
    collections.add_entry(collection.id, entry.id)

    entries.delete(entry.id)

    assert collections.list_entries(collection.id) == []
