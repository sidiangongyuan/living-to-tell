"""Brand migration tests for local data paths."""
from __future__ import annotations

from pathlib import Path

from writer.app import paths as paths_module


def test_database_path_copies_legacy_writer_data_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv(paths_module.ENV_DATA_DIR, raising=False)

    new_dir = tmp_path / "new" / paths_module.APP_AUTHOR / paths_module.APP_NAME
    legacy_dir = (
        tmp_path
        / "legacy"
        / paths_module.LEGACY_APP_AUTHOR
        / paths_module.LEGACY_APP_NAME
    )

    def fake_user_data_dir(appname: str, appauthor: str, roaming: bool) -> str:
        assert roaming is True
        if appname == paths_module.APP_NAME and appauthor == paths_module.APP_AUTHOR:
            return str(new_dir)
        if (
            appname == paths_module.LEGACY_APP_NAME
            and appauthor == paths_module.LEGACY_APP_AUTHOR
        ):
            return str(legacy_dir)
        raise AssertionError(f"unexpected app data request: {appauthor}/{appname}")

    monkeypatch.setattr(paths_module, "user_data_dir", fake_user_data_dir)

    legacy_dir.mkdir(parents=True)
    legacy_db = legacy_dir / paths_module.LEGACY_DATABASE_FILENAME
    legacy_db.write_bytes(b"legacy sqlite bytes")
    Path(f"{legacy_db}-wal").write_bytes(b"legacy wal bytes")
    (legacy_dir / "backups").mkdir()
    (legacy_dir / "backups" / "backup.txt").write_text("backup", encoding="utf-8")

    db_path = paths_module.database_path()

    assert db_path == new_dir / paths_module.DATABASE_FILENAME
    assert db_path.read_bytes() == b"legacy sqlite bytes"
    assert Path(f"{db_path}-wal").read_bytes() == b"legacy wal bytes"
    assert (new_dir / "backups" / "backup.txt").read_text(encoding="utf-8") == "backup"
    assert legacy_db.exists(), "legacy Writer database must be retained"

    db_path.write_bytes(b"new database")
    legacy_db.write_bytes(b"changed legacy database")
    assert paths_module.database_path().read_bytes() == b"new database"


def test_wrapped_data_dir_skips_legacy_migration(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "override"
    monkeypatch.setenv(paths_module.ENV_DATA_DIR, str(override))

    def fail_user_data_dir(*_args, **_kwargs) -> str:
        raise AssertionError("WRITER_DATA_DIR should bypass platform user data lookup")

    monkeypatch.setattr(paths_module, "user_data_dir", fail_user_data_dir)

    assert paths_module.database_path() == override / paths_module.DATABASE_FILENAME
    assert override.exists()
