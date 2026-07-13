import sqlite3

import pytest

from writer.storage.database import initialize_schema
from writer.storage.database import open_and_initialize
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.motif_repository import MotifRepository
from writer.storage.repositories.reference_repository import ReferenceRepository


def test_motif_excerpt_can_link_multiple_nodes_and_build_graph(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="花园", body="玫瑰在夜里像血一样醒着。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="玫瑰在夜里像血一样醒着。",
        motif_names=["玫瑰", "血"],
        selection_start=0,
        selection_end=13,
        before_context="",
        after_context="",
    )

    assert excerpt.source_exists is True
    assert excerpt.source_current_title == "花园"
    assert excerpt.motif_names == ["玫瑰", "血"]

    nodes = motifs.list_nodes()
    assert {node.name for node in nodes} == {"玫瑰", "血"}
    assert {node.excerpt_count for node in nodes} == {1}

    graph_nodes, graph_edges = motifs.graph(limit=20)
    assert {node.name for node in graph_nodes} == {"玫瑰", "血"}
    assert len(graph_edges) == 1
    assert graph_edges[0].shared_excerpts == 1
    assert graph_edges[0].shared_sources == 1
    assert graph_edges[0].weight == 3


def test_motif_excerpt_snapshot_survives_source_deletion(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="旧稿", body="门后有雨。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="门后有雨。",
        motif_names=["门"],
    )
    entries.delete(entry.id)

    loaded = motifs.get_excerpt(excerpt.id)
    assert loaded is not None
    assert loaded.excerpt_text == "门后有雨。"
    assert loaded.source_exists is False
    assert loaded.source_title_snapshot == "旧稿"


def test_motif_node_crud_and_delete_keeps_source(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="井", body="井底有一枚月亮。")
    node = motifs.create_node(name="井", aliases=["水眼"], tags=["空间"], pinned=True)
    updated = motifs.update_node(
        node.id,
        name="古井",
        aliases=["井"],
        tags=["空间", "回声"],
        note="反复出现的下沉意象。",
        pinned=False,
    )
    assert updated is not None
    assert updated.name == "古井"
    assert updated.aliases == ["井"]
    assert updated.tags == ["空间", "回声"]
    assert updated.note == "反复出现的下沉意象。"
    assert updated.pinned is False

    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="井底有一枚月亮。",
        motif_ids=[updated.id],
    )
    assert motifs.delete_node(updated.id) is True
    assert entries.get(entry.id) is not None
    assert motifs.get_excerpt(excerpt.id) is None


def test_motif_node_profile_persists_and_searches(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    motifs = MotifRepository(conn)

    profile = {
        "definition": "人在公共意见中失去自己的判断。",
        "core_tension": "自我选择与平均化生活互相拉扯。",
        "writing_functions": ["制造日常压力"],
        "source_hints": [{"title": "《存在与时间》", "url": None, "note": "需核对"}],
    }
    node = motifs.create_node(
        name="海德格尔的常人",
        tags=["哲学概念"],
        profile=profile,
    )
    loaded = motifs.get_node(node.id)

    assert loaded is not None
    assert loaded.profile["definition"] == profile["definition"]
    assert loaded.profile["writing_functions"] == ["制造日常压力"]
    assert motifs.list_nodes(query="平均化生活", limit=10)[0].id == node.id

    updated = motifs.update_node(
        node.id,
        name=node.name,
        tags=["哲学概念", "存在主义"],
        profile={**profile, "definition": "常人是日常公共性中的平均化自我。"},
    )
    assert updated is not None
    assert updated.profile["definition"] == "常人是日常公共性中的平均化自我。"

    preserved = motifs.update_node(
        node.id,
        name=node.name,
        tags=["哲学概念"],
        note="只改自由笔记，不清空档案。",
    )
    assert preserved is not None
    assert preserved.profile["definition"] == "常人是日常公共性中的平均化自我。"


def test_motif_excerpt_can_use_reference_source(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    references = ReferenceRepository(conn)
    motifs = MotifRepository(conn)

    reference = references.create(
        source_title="夜航西飞",
        source_author="柏瑞尔·马卡姆",
        content="天空像一块被擦亮的黑石。",
        usage_kind="imagery",
    )
    excerpt = motifs.create_excerpt(
        source_kind="reference",
        source_id=reference.id,
        excerpt_text="天空像一块被擦亮的黑石。",
        motif_names=["天空", "黑石"],
    )

    assert excerpt.source_exists is True
    assert excerpt.source_current_title == "夜航西飞"
    assert excerpt.source_kind == "reference"
    graph_nodes, graph_edges = motifs.graph(limit=20)
    assert {node.name for node in graph_nodes} == {"天空", "黑石"}
    assert graph_edges[0].shared_excerpts == 1
    assert graph_edges[0].shared_sources == 1


def test_motif_excerpt_same_source_and_selection_merges_motifs(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="城市", body="城市有雨。城市有雨。")
    first = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="城市有雨。",
        motif_names=["城市"],
        selection_start=0,
        selection_end=5,
    )
    second = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="城市有雨。",
        motif_names=["雨"],
        selection_start=0,
        selection_end=5,
    )

    assert second.id == first.id
    assert set(second.motif_names) == {"城市", "雨"}
    assert conn.execute("SELECT COUNT(*) AS n FROM motif_excerpts").fetchone()["n"] == 1


def test_motif_excerpt_same_text_different_positions_stays_distinct(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="回声", body="门开了。门开了。")
    first = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="门开了。",
        motif_names=["门"],
        selection_start=0,
        selection_end=4,
    )
    second = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="门开了。",
        motif_names=["回声"],
        selection_start=4,
        selection_end=8,
    )

    assert second.id != first.id
    assert conn.execute("SELECT COUNT(*) AS n FROM motif_excerpts").fetchone()["n"] == 2


def test_motif_excerpt_lookup_repairs_stale_range_when_text_is_unique(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    sentence = "裙摆在移动间带起一阵微弱的风，那股苦杏仁的味道随之变得浓郁，又迅速在空气中稀释。"
    body = f"前文被加长了。\n\n{sentence}\n\n后文。"
    entry = entries.create(title="苦杏仁、凉面与那一阵风", body=body)
    current_start = body.index(sentence)
    current_end = current_start + len(sentence)
    stale_start = max(0, current_start - 7)
    stale = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        motif_names=["测试意象｜往事", "测试意象｜风"],
        selection_start=stale_start,
        selection_end=stale_start + len(sentence),
    )

    found = motifs.find_excerpt_for_selection(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        selection_start=current_start,
        selection_end=current_end,
        before_context=body[max(0, current_start - 90):current_start],
        after_context=body[current_end:current_end + 90],
    )

    assert found is not None
    assert found.id == stale.id
    assert found.selection_start == current_start
    assert found.selection_end == current_end
    assert set(found.motif_names) == {"测试意象｜往事", "测试意象｜风"}


def test_motif_source_repair_merges_duplicate_excerpt_at_same_current_range(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    sentence = "裙摆在移动间带起一阵微弱的风，那股苦杏仁的味道随之变得浓郁，又迅速在空气中稀释。"
    body = f"前文。\n\n{sentence}\n\n后文。"
    entry = entries.create(title="苦杏仁、凉面与那一阵风", body=body)
    current_start = body.index(sentence)
    current_end = current_start + len(sentence)
    first = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        motif_names=["测试意象｜往事"],
        note="第一条备注",
        selection_start=current_start,
        selection_end=current_end,
    )
    past = motifs.find_node_by_name("测试意象｜往事")
    wind = motifs.create_node(name="测试意象｜风")
    assert past is not None
    duplicate_id = "duplicate-stale-range"
    conn.execute(
        """
        INSERT INTO motif_excerpts
            (id, source_kind, source_id, source_title_snapshot, excerpt_text, note,
             selection_start, selection_end, before_context, after_context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            duplicate_id,
            "article",
            entry.id,
            entry.title,
            sentence,
            "第二条备注",
            current_start + 60,
            current_end + 60,
            "",
            "",
        ),
    )
    conn.execute(
        """
        INSERT INTO motif_excerpt_links (id, motif_id, excerpt_id)
        VALUES (?, ?, ?)
        """,
        ("duplicate-link", wind.id, duplicate_id),
    )

    repaired = motifs.list_excerpts_for_source("article", entry.id)

    assert len(repaired) == 1
    assert repaired[0].id == first.id
    assert repaired[0].selection_start == current_start
    assert repaired[0].selection_end == current_end
    assert set(repaired[0].motif_names) == {"测试意象｜往事", "测试意象｜风"}
    assert "第一条备注" in repaired[0].note
    assert "第二条备注" in repaired[0].note
    assert conn.execute("SELECT COUNT(*) AS n FROM motif_excerpts").fetchone()["n"] == 1


def test_motif_lookup_does_not_merge_same_text_at_different_current_positions(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    sentence = "门开了。"
    body = f"{sentence}中间。{sentence}"
    entry = entries.create(title="回声", body=body)
    first_start = body.index(sentence)
    first_end = first_start + len(sentence)
    second_start = body.rindex(sentence)
    second_end = second_start + len(sentence)
    first = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        motif_names=["门"],
        selection_start=first_start,
        selection_end=first_end,
    )
    second = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        motif_names=["回声"],
        selection_start=second_start,
        selection_end=second_end,
    )

    assert first.id != second.id
    first_lookup = motifs.find_excerpt_for_selection(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        selection_start=first_start,
        selection_end=first_end,
    )
    second_lookup = motifs.find_excerpt_for_selection(
        source_kind="article",
        source_id=entry.id,
        excerpt_text=sentence,
        selection_start=second_start,
        selection_end=second_end,
    )

    assert first_lookup is not None and first_lookup.id == first.id
    assert second_lookup is not None and second_lookup.id == second.id
    assert conn.execute("SELECT COUNT(*) AS n FROM motif_excerpts").fetchone()["n"] == 2


def test_motif_excerpt_lookup_falls_back_to_text_without_selection(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="风", body="一阵风。")
    created = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="一阵风。",
        motif_names=["风"],
    )

    found = motifs.find_excerpt_for_selection(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="一阵风。",
    )

    assert found is not None
    assert found.id == created.id


def test_unlink_motif_from_excerpt_keeps_other_motifs(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="岁月", body="岁月穿过城市。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="岁月穿过城市。",
        motif_names=["岁月", "城市"],
    )
    years = motifs.find_node_by_name("岁月")
    city = motifs.find_node_by_name("城市")
    assert years is not None and city is not None

    assert motifs.unlink_motif_from_excerpt(excerpt.id, years.id) is True

    assert motifs.get_excerpt(excerpt.id) is not None
    assert motifs.list_excerpts_for_node(years.id) == []
    city_excerpts = motifs.list_excerpts_for_node(city.id)
    assert [item.id for item in city_excerpts] == [excerpt.id]


def test_set_motifs_for_excerpt_replaces_existing_links(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="城市", body="岁月穿过城市。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="岁月穿过城市。",
        motif_names=["岁月", "城市"],
    )
    years = motifs.find_node_by_name("岁月")
    city = motifs.find_node_by_name("城市")
    message = motifs.create_node(name="消息")
    assert years is not None and city is not None

    existed, updated = motifs.set_motifs_for_excerpt(
        excerpt.id,
        motif_ids=[city.id],
        motif_names=["消息"],
        note="更新后的备注",
    )

    assert existed is True
    assert updated is not None
    assert set(updated.motif_names) == {"城市", "消息"}
    assert updated.note == "更新后的备注"
    assert motifs.list_excerpts_for_node(years.id) == []
    assert [item.id for item in motifs.list_excerpts_for_node(city.id)] == [excerpt.id]
    assert [item.id for item in motifs.list_excerpts_for_node(message.id)] == [excerpt.id]


def test_set_motifs_for_excerpt_empty_set_deletes_orphan_excerpt(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="城市", body="岁月穿过城市。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="岁月穿过城市。",
        motif_names=["岁月"],
    )
    node = motifs.find_node_by_name("岁月")
    assert node is not None

    existed, updated = motifs.set_motifs_for_excerpt(excerpt.id, motif_names=[])

    assert existed is True
    assert updated is None
    assert motifs.get_excerpt(excerpt.id) is None
    assert motifs.list_excerpts_for_node(node.id) == []


def test_unlink_last_motif_deletes_orphan_excerpt(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)

    entry = entries.create(title="月亮", body="月亮落下。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="月亮落下。",
        motif_names=["月亮"],
    )
    node = motifs.find_node_by_name("月亮")
    assert node is not None

    assert motifs.unlink_motif_from_excerpt(excerpt.id, node.id) is True

    assert motifs.get_excerpt(excerpt.id) is None
    assert motifs.list_excerpts_for_node(node.id) == []


def test_motif_excerpt_validation_rejects_empty_or_invalid_payload(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)
    entry = entries.create(title="空句", body="一阵风。")

    with pytest.raises(ValueError, match="Excerpt text is required"):
        motifs.create_excerpt(
            source_kind="article",
            source_id=entry.id,
            excerpt_text="  ",
            motif_names=["风"],
        )
    with pytest.raises(ValueError, match="Unsupported motif source kind"):
        motifs.create_excerpt(
            source_kind="collection",
            source_id=entry.id,
            excerpt_text="一阵风。",
            motif_names=["风"],
        )
    with pytest.raises(ValueError, match="At least one motif is required"):
        motifs.create_excerpt(
            source_kind="article",
            source_id=entry.id,
            excerpt_text="一阵风。",
            motif_names=[],
        )


def test_motif_schema_initialization_is_idempotent(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    initialize_schema(conn)
    table_names = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'motif_%'"
        ).fetchall()
    }
    assert {
        "motif_nodes",
        "motif_excerpts",
        "motif_excerpt_links",
        "motif_relations",
    }.issubset(table_names)


def test_motif_relation_crud_normalizes_direction_and_cascades(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    motifs = MotifRepository(conn)
    rain = motifs.create_node(name="雨")
    river = motifs.create_node(name="河流")

    created = motifs.upsert_relation(
        rain.id,
        target_node_id=river.id,
        relation_type="transformation",
        direction_from_current="from_current",
        reason="雨汇入河流。",
    )
    expected_direction = "a_to_b" if created.motif_a_id == rain.id else "b_to_a"
    assert created.direction == expected_direction
    assert created.reason == "雨汇入河流。"

    updated = motifs.update_relation(
        river.id,
        created.id,
        relation_type="contains",
        direction_from_current="from_current",
        reason="河流包含雨水。",
    )
    assert updated is not None
    assert updated.id == created.id
    assert updated.relation_type == "contains"
    expected_reverse = "a_to_b" if updated.motif_a_id == river.id else "b_to_a"
    assert updated.direction == expected_reverse

    undirected = motifs.upsert_relation(
        rain.id,
        target_node_id=river.id,
        relation_type="contrast",
        direction_from_current="from_current",
    )
    assert undirected.id == created.id
    assert undirected.direction == "undirected"
    assert len(motifs.list_relations(rain.id)) == 1

    assert motifs.delete_node(river.id) is True
    assert motifs.list_relations(rain.id) == []
    assert conn.execute("SELECT COUNT(*) AS n FROM motif_relations").fetchone()["n"] == 0


def test_motif_graph_merges_cooccurrence_and_authored_relationship_sources(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    entries = EntryRepository(conn)
    motifs = MotifRepository(conn)
    entry = entries.create(title="夜雨", body="雨敲在窗上。")
    excerpt = motifs.create_excerpt(
        source_kind="article",
        source_id=entry.id,
        excerpt_text="雨敲在窗上。",
        motif_names=["雨", "窗"],
    )
    rain = motifs.find_node_by_name("雨")
    window = motifs.find_node_by_name("窗")
    dawn = motifs.create_node(name="黎明")
    assert rain is not None and window is not None

    cooccurrence_relation = motifs.upsert_relation(
        rain.id,
        target_node_id=window.id,
        relation_type="echo",
        reason="声音彼此呼应。",
    )
    authored_only = motifs.upsert_relation(
        rain.id,
        target_node_id=dawn.id,
        relation_type="contrast",
    )

    graph_nodes, graph_edges = motifs.graph(limit=20)
    by_pair = {frozenset((edge.source_id, edge.target_id)): edge for edge in graph_edges}
    rain_window = by_pair[frozenset((rain.id, window.id))]
    assert rain_window.shared_excerpts == 1
    assert rain_window.shared_sources == 1
    assert rain_window.relation_id == cooccurrence_relation.id
    assert rain_window.relation_type == "echo"
    assert by_pair[frozenset((rain.id, dawn.id))].relation_id == authored_only.id
    assert by_pair[frozenset((rain.id, dawn.id))].shared_excerpts == 0
    assert {node.name: node.relation_count for node in graph_nodes}["雨"] == 2

    assert motifs.delete_relation(rain.id, cooccurrence_relation.id) is True
    _, after_relation_delete = motifs.graph(limit=20)
    remaining_pair = {
        frozenset((edge.source_id, edge.target_id)): edge
        for edge in after_relation_delete
    }[frozenset((rain.id, window.id))]
    assert remaining_pair.relation_id is None
    assert remaining_pair.shared_excerpts == 1

    assert motifs.delete_excerpt(excerpt.id) is True
    _, after_excerpt_delete = motifs.graph(limit=20)
    final_pairs = {frozenset((edge.source_id, edge.target_id)) for edge in after_excerpt_delete}
    assert frozenset((rain.id, window.id)) not in final_pairs
    assert frozenset((rain.id, dawn.id)) in final_pairs


def test_apply_motif_relation_candidates_is_idempotent_and_reuses_alias(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    motifs = MotifRepository(conn)
    current = motifs.create_node(name="夜")
    existing = motifs.create_node(name="黎明", aliases=["晨光"])
    candidates = [
        {
            "kind": "new",
            "name": "晨光",
            "relation_type": "contrast",
            "direction": "undirected",
            "reason": "夜与晨光相对。",
        },
        {
            "kind": "new",
            "name": "门槛",
            "relation_type": "associated",
            "direction": "undirected",
            "reason": "都指向过渡。",
        },
    ]

    first_relations, first_created, first_skipped = motifs.apply_relation_candidates(
        current.id, candidates
    )
    second_relations, second_created, second_skipped = motifs.apply_relation_candidates(
        current.id, candidates
    )

    assert first_skipped == second_skipped == []
    assert [node.name for node in first_created] == ["门槛"]
    assert second_created == []
    assert {relation.id for relation in first_relations} == {
        relation.id for relation in second_relations
    }
    assert motifs.find_node_by_name_or_alias("晨光").id == existing.id
    assert len(motifs.list_relations(current.id)) == 2
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM motif_nodes WHERE lower(name) = lower(?)",
        ("门槛",),
    ).fetchone()["n"] == 1


def test_apply_motif_relation_candidates_rolls_back_new_nodes_on_invalid_batch(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    motifs = MotifRepository(conn)
    current = motifs.create_node(name="火")

    with pytest.raises(ValueError, match="必须选择方向"):
        motifs.apply_relation_candidates(
            current.id,
            [
                {
                    "kind": "new",
                    "name": "灰烬",
                    "relation_type": "transformation",
                    "direction": "undirected",
                }
            ],
        )

    assert motifs.find_node_by_name("灰烬") is None
    assert motifs.list_relations(current.id) == []


def test_legacy_database_initialization_adds_motif_relations_without_losing_nodes(tmp_path):
    database_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(database_path)
    legacy.executescript(
        """
        CREATE TABLE motif_nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            aliases_text TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            profile_json TEXT NOT NULL DEFAULT '{}',
            tags_text TEXT NOT NULL DEFAULT '',
            pinned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '2026-01-01T00:00:00Z',
            updated_at TEXT NOT NULL DEFAULT '2026-01-01T00:00:00Z'
        );
        INSERT INTO motif_nodes (id, name) VALUES ('legacy-motif', '旧意象');
        """
    )
    legacy.commit()
    legacy.close()

    conn = open_and_initialize(database_path)
    motifs = MotifRepository(conn)

    assert motifs.get_node("legacy-motif").name == "旧意象"
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table' AND name = 'motif_relations'"
    ).fetchone()["n"] == 1
