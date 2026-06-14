"""Shared dependencies: the long-lived AppContainer singleton.

The container holds the SQLite connection plus every repository and service.
FastAPI route handlers depend on ``get_container`` to reach the existing
``writer`` backend without any duplication.
"""
from __future__ import annotations

from functools import lru_cache

# Configure the data dir BEFORE importing anything from writer.* so the
# database lands in the right place.
from config import configure_data_dir

configure_data_dir()

from writer.app.container import AppContainer, build_container  # noqa: E402


class ExtendedAppContainer(AppContainer):
    """扩展的应用容器，添加 Tauri MVP 专用服务。"""

    def __init__(self, base_container: AppContainer):
        # 复制基础容器的所有属性
        self.__dict__.update(base_container.__dict__)

        # 延迟导入避免循环依赖
        from features.backup.service import BackupService

        # 添加备份服务
        db_path = base_container.connection.execute("PRAGMA database_list").fetchone()[2]
        self.backup_service = BackupService(db_path)


@lru_cache(maxsize=1)
def get_container() -> ExtendedAppContainer:
    """Return the process-wide ExtendedAppContainer, building it on first use."""
    base = build_container()
    return ExtendedAppContainer(base)
