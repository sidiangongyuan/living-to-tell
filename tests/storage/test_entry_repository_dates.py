"""Tests for the M-Dates additions to EntryRepository."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from writer.storage.database import open_and_initialize
from writer.storage.repositories.entry_repository import (
    DailyStat,
    EntryRepository,
)


@pytest.fixture()
def repo(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    try:
        yield EntryRepository(conn)
    finally:
        conn.close()


def _set_created_at(conn, entry_id: str, when_utc: datetime) -> None:
    iso = when_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    conn.execute(
        "UPDATE entries SET created_at = ? WHERE id = ?", (iso, entry_id)
    )


def _local_to_utc(local_dt: datetime) -> datetime:
    """Treat ``local_dt`` as local-tz wall-clock and return its UTC instant."""
    local_tz = datetime.now().astimezone().tzinfo
    return local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)


def test_list_by_local_date_filters_only_target_day(repo):
    today = date.today()
    yesterday = today - timedelta(days=1)
    e_today = repo.create(title="Today", body="hello world")
    e_y = repo.create(title="Yesterday", body="ancient")
    # Force one entry into yesterday's local day.
    _set_created_at(
        repo._conn,
        e_y.id,
        _local_to_utc(datetime.combine(yesterday, time(12, 0))),
    )

    result = repo.list_by_local_date(today)
    ids = {e.id for e in result}
    assert e_today.id in ids
    assert e_y.id not in ids


def test_list_by_local_date_handles_late_night_local(repo):
    """An entry created at 23:30 local should still bucket into that day."""
    today = date.today()
    e = repo.create(title="late", body="x")
    _set_created_at(
        repo._conn, e.id, _local_to_utc(datetime.combine(today, time(23, 30)))
    )
    result = repo.list_by_local_date(today)
    assert e.id in {x.id for x in result}


def test_daily_stats_for_month_aggregates_word_count(repo):
    today = date.today()
    e1 = repo.create(title="a", body="one two three")  # 3 words
    e2 = repo.create(title="b", body="alpha beta")  # 2 words
    # Force both onto same local day if today.
    iso_today = _local_to_utc(datetime.combine(today, time(10, 0)))
    _set_created_at(repo._conn, e1.id, iso_today)
    _set_created_at(repo._conn, e2.id, iso_today)

    stats = repo.daily_stats_for_month(today.year, today.month)
    assert today in stats
    s = stats[today]
    assert isinstance(s, DailyStat)
    assert s.entry_count == 2
    assert s.total_word_count == 5
    assert s.has_curated is False


def test_daily_stats_excludes_archived_by_default(repo):
    today = date.today()
    e_keep = repo.create(title="keep", body="words words")
    e_drop = repo.create(title="drop", body="archived")
    repo.set_archived(e_drop.id, True)

    stats = repo.daily_stats_for_month(today.year, today.month)
    assert stats.get(today) is not None
    assert stats[today].entry_count == 1


def test_append_tags_dedups_case_insensitive_and_preserves_order(repo):
    e = repo.create(title="t", body="b", tags=["Plot", "Idea"])
    updated = repo.append_tags(e.id, ["plot", "Theme", " IDEA "])
    assert updated is not None
    assert updated.tags == ["Plot", "Idea", "Theme"]


def test_append_tags_empty_list_is_noop(repo):
    e = repo.create(title="t", body="b", tags=["A"])
    same = repo.append_tags(e.id, [])
    assert same is not None
    assert same.tags == ["A"]


def test_append_tags_unknown_id_returns_none(repo):
    assert repo.append_tags("does-not-exist", ["x"]) is None
