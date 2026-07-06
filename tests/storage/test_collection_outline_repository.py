from __future__ import annotations

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_collection_outline_crud_and_order(container):
    collection = container.collection_repository.create("Novel")
    article = container.entry_repository.create(title="Chapter draft", body="body")

    first = container.collection_outline_repository.create(
        collection.id,
        title="第一部",
        item_type="part",
        status="idea",
    )
    second = container.collection_outline_repository.create(
        collection.id,
        title="雨夜来信",
        item_type="scene",
        status="drafting",
        entry_id=article.id,
        summary="一次推动关系的来信。",
        tags=["爱情", "等待"],
        target_word_count=2500,
    )

    assert first is not None
    assert second is not None
    assert [item.id for item in container.collection_outline_repository.list_for_collection(collection.id)] == [
        first.id,
        second.id,
    ]
    assert second.tags == ["爱情", "等待"]

    updated = container.collection_outline_repository.update(
        second.id,
        title="雨夜来信修订",
        item_type="chapter",
        status="revising",
        summary="修订摘要",
        notes="目标 / 冲突 / 转折 / 结局",
        parent_id=first.id,
        entry_id=article.id,
        pov="她",
        setting="老屋",
        timeline="冬夜",
        tags=["等待"],
        target_word_count=3200,
    )

    assert updated is not None
    assert updated.parent_id == first.id
    assert updated.status == "revising"
    assert updated.tags == ["等待"]

    reordered = container.collection_outline_repository.reorder(
        collection.id,
        [second.id, first.id],
    )
    assert [item.id for item in reordered] == [second.id, first.id]


def test_collection_outline_preserves_children_when_parent_is_deleted(container):
    collection = container.collection_repository.create("Essays")
    parent = container.collection_outline_repository.create(
        collection.id,
        title="第一组",
        item_type="part",
    )
    child = container.collection_outline_repository.create(
        collection.id,
        title="散文条目",
        item_type="note",
        parent_id=parent.id,
    )

    assert container.collection_outline_repository.delete(parent.id) is True

    remaining = container.collection_outline_repository.get(child.id)
    assert remaining is not None
    assert remaining.parent_id is None


def test_collection_outline_rejects_bad_links(container):
    collection = container.collection_repository.create("Novel")
    item = container.collection_outline_repository.create(collection.id, title="Scene")
    assert item is not None

    with pytest.raises(ValueError):
        container.collection_outline_repository.update(
            item.id,
            title="Bad",
            item_type="scene",
            status="idea",
            parent_id=item.id,
        )

    with pytest.raises(ValueError):
        container.collection_outline_repository.create(
            collection.id,
            title="Missing article",
            entry_id="missing-entry",
        )


def test_collection_outline_rejects_parent_cycle(container):
    collection = container.collection_repository.create("Novel")
    parent = container.collection_outline_repository.create(
        collection.id,
        title="Part",
        item_type="part",
    )
    child = container.collection_outline_repository.create(
        collection.id,
        title="Chapter",
        item_type="chapter",
        parent_id=parent.id,
    )

    with pytest.raises(ValueError):
        container.collection_outline_repository.update(
            parent.id,
            title="Bad parent",
            item_type="part",
            status="idea",
            parent_id=child.id,
        )
