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
        item_type="chapter",
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
        title="散文章节",
        item_type="chapter",
        parent_id=parent.id,
    )

    assert container.collection_outline_repository.delete(parent.id) is True

    remaining = container.collection_outline_repository.get(child.id)
    assert remaining is not None
    assert remaining.parent_id is None


def test_collection_outline_rejects_bad_links(container):
    collection = container.collection_repository.create("Novel")
    item = container.collection_outline_repository.create(
        collection.id,
        title="Chapter",
        item_type="chapter",
    )
    assert item is not None

    with pytest.raises(ValueError):
        container.collection_outline_repository.update(
            item.id,
            title="Bad",
            item_type="chapter",
            status="idea",
            parent_id=item.id,
        )

    with pytest.raises(ValueError):
        container.collection_outline_repository.create(
            collection.id,
            title="Missing article",
            item_type="chapter",
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


def test_collection_outline_enforces_structure_and_unique_article(container):
    collection = container.collection_repository.create(
        "Essays",
        project_type="essay",
    )
    article = container.entry_repository.create(title="真实文章", body="正文")
    part = container.collection_outline_repository.create(
        collection.id,
        title="第一辑",
        item_type="part",
    )
    chapter = container.collection_outline_repository.create(
        collection.id,
        title="人生哲思",
        item_type="chapter",
        parent_id=part.id,
    )
    leaf = container.collection_outline_repository.create(
        collection.id,
        title="旧规划标题",
        item_type="scene",
        parent_id=chapter.id,
        entry_id=article.id,
    )

    assert leaf is not None
    with pytest.raises(ValueError, match="已经放在"):
        container.collection_outline_repository.create(
            collection.id,
            title="重复位置",
            item_type="chapter",
            entry_id=article.id,
        )
    with pytest.raises(ValueError, match="顶层"):
        container.collection_outline_repository.create(
            collection.id,
            title="错误正文",
            item_type="scene",
            entry_id=container.entry_repository.create(title="B").id,
        )
    with pytest.raises(ValueError, match="不能关联正文"):
        container.collection_outline_repository.update(
            part.id,
            title=part.title,
            item_type="part",
            status=part.status,
            entry_id=container.entry_repository.create(title="C").id,
        )
    with pytest.raises(ValueError, match="先将它拆成子项"):
        container.collection_outline_repository.create(
            collection.id,
            title="不能直接放在已关联章节下",
            item_type="scene",
            parent_id=container.collection_outline_repository.create(
                collection.id,
                title="直接正文",
                item_type="chapter",
                entry_id=container.entry_repository.create(title="D").id,
            ).id,
        )
    with pytest.raises(ValueError, match="父子层级"):
        container.collection_outline_repository.create(
            collection.id,
            title="叶节点的子项",
            item_type="note",
            parent_id=leaf.id,
        )


def test_collection_outline_make_container_is_transactional_and_idempotent(container):
    collection = container.collection_repository.create(
        "Novel",
        project_type="novel",
    )
    article = container.entry_repository.create(title="改名后的正文", body="正文")
    chapter = container.collection_outline_repository.create(
        collection.id,
        title="规划标题",
        item_type="chapter",
        status="drafting",
        entry_id=article.id,
        target_word_count=3000,
    )

    parent, child, changed = container.collection_outline_repository.make_container(
        chapter.id,
        collection_id=collection.id,
    )

    assert changed is True
    assert parent is not None and parent.entry_id is None
    assert parent.target_word_count is None
    assert child is not None
    assert child.parent_id == chapter.id
    assert child.entry_id == article.id
    assert child.title == "改名后的正文"
    assert child.target_word_count == 3000

    same_parent, duplicate_child, changed_again = (
        container.collection_outline_repository.make_container(
            chapter.id,
            collection_id=collection.id,
        )
    )
    assert same_parent is not None
    assert duplicate_child is None
    assert changed_again is False
    assert len(container.collection_outline_repository.list_for_collection(collection.id)) == 2


def test_collection_outline_status_update_does_not_touch_children(container):
    collection = container.collection_repository.create("Book")
    chapter = container.collection_outline_repository.create(
        collection.id,
        title="Chapter",
        item_type="chapter",
    )
    child = container.collection_outline_repository.create(
        collection.id,
        title="Article",
        item_type="scene",
        parent_id=chapter.id,
        status="drafting",
    )

    updated = container.collection_outline_repository.update_status(
        chapter.id,
        "done",
        collection_id=collection.id,
    )

    assert updated is not None and updated.status == "done"
    assert container.collection_outline_repository.get(child.id).status == "drafting"


def test_collection_outline_refuses_delete_that_would_orphan_invalid_children(container):
    collection = container.collection_repository.create("Book")
    chapter = container.collection_outline_repository.create(
        collection.id,
        title="Chapter",
        item_type="chapter",
    )
    child = container.collection_outline_repository.create(
        collection.id,
        title="Article",
        item_type="scene",
        parent_id=chapter.id,
    )

    with pytest.raises(ValueError, match="仍有子项"):
        container.collection_outline_repository.delete(chapter.id)

    assert container.collection_outline_repository.get(chapter.id) is not None
    assert container.collection_outline_repository.get(child.id).parent_id == chapter.id
