"""数据备份与检查点管理服务。

提供：
1. 自动备份：定期备份整个数据库
2. 手动检查点：用户标记的重要版本节点
3. 恢复功能：从备份或检查点恢复
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from writer.app.paths import user_data_directory


class BackupService:
    """数据库备份与检查点服务。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_dir = Path(user_data_directory()) / "backups"
        self.checkpoint_dir = Path(user_data_directory()) / "checkpoints"

        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_auto_backup(self) -> str:
        """创建自动备份。

        Returns:
            备份文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"auto_backup_{timestamp}.sqlite3"
        backup_path = self.backup_dir / backup_name

        self._vacuum_into(backup_path)

        # 清理旧的自动备份（保留最近 10 个）
        self._cleanup_old_backups()

        return str(backup_path)

    def create_checkpoint(self, name: str, description: str = "") -> str:
        """创建用户检查点。

        Args:
            name: 检查点名称
            description: 检查点描述

        Returns:
            检查点文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理文件名（移除特殊字符）
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name)
        checkpoint_name = f"checkpoint_{timestamp}_{safe_name}.sqlite3"
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        self._vacuum_into(checkpoint_path)

        # 保存元数据
        meta_path = checkpoint_path.with_suffix('.meta.txt')
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(f"Name: {name}\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
            f.write(f"Description: {description}\n")

        return str(checkpoint_path)

    def list_backups(self) -> List[dict]:
        """列出所有自动备份。

        Returns:
            备份列表，每项包含 path, name, size, created
        """
        backups = []
        for file in sorted(self.backup_dir.glob("auto_backup_*.sqlite3"), reverse=True):
            stat = file.stat()
            backups.append({
                'path': str(file),
                'name': file.stem,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return backups

    def list_checkpoints(self) -> List[dict]:
        """列出所有检查点。

        Returns:
            检查点列表
        """
        checkpoints = []
        for file in sorted(self.checkpoint_dir.glob("checkpoint_*.sqlite3"), reverse=True):
            stat = file.stat()

            # 读取元数据
            meta_path = file.with_suffix('.meta.txt')
            meta = {}
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            meta[key.strip()] = value.strip()

            checkpoints.append({
                'path': str(file),
                'name': meta.get('Name', file.stem),
                'description': meta.get('Description', ''),
                'size': stat.st_size,
                'created': meta.get('Created', datetime.fromtimestamp(stat.st_mtime).isoformat()),
            })
        return checkpoints

    def restore_from_backup(self, backup_path: str) -> bool:
        """从备份恢复数据库。

        Args:
            backup_path: 备份文件路径

        Returns:
            是否成功
        """
        source = Path(backup_path)
        if not source.exists() or not source.is_file():
            return False

        # 先备份当前数据库
        self.create_auto_backup()

        # 替换数据库。调用方应先关闭长期 SQLite 连接；这里同时清理
        # WAL/SHM sidecar，避免恢复后旧 WAL 被重新 replay。
        self._remove_sqlite_sidecars(Path(self.db_path))
        shutil.copy2(source, self.db_path)
        self._remove_sqlite_sidecars(Path(self.db_path))
        return True

    def _vacuum_into(self, target_path: Path) -> None:
        """Create a consistent SQLite copy without interpolating file paths."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
            conn.execute("VACUUM INTO ?", (str(target_path),))
        finally:
            conn.close()

    @staticmethod
    def _remove_sqlite_sidecars(db_path: Path) -> None:
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(f"{db_path}{suffix}")
            try:
                sidecar.unlink(missing_ok=True)
            except OSError:
                pass

    def delete_backup(self, backup_path: str) -> bool:
        """删除备份。

        Args:
            backup_path: 备份文件路径

        Returns:
            是否成功
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                return True
        except Exception:
            pass
        return False

    def delete_checkpoint(self, checkpoint_path: str) -> bool:
        """删除检查点。

        Args:
            checkpoint_path: 检查点文件路径

        Returns:
            是否成功
        """
        try:
            checkpoint = Path(checkpoint_path)
            if checkpoint.exists():
                checkpoint.unlink()
                # 同时删除元数据
                meta_path = checkpoint.with_suffix('.meta.txt')
                if meta_path.exists():
                    meta_path.unlink()
                return True
        except Exception:
            pass
        return False

    def _cleanup_old_backups(self, keep_count: int = 10):
        """清理旧的自动备份，保留最近 N 个。"""
        backups = sorted(
            self.backup_dir.glob("auto_backup_*.sqlite3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # 删除超出保留数量的备份
        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink()
            except Exception:
                pass

    def get_backup_stats(self) -> dict:
        """获取备份统计信息。"""
        backups = self.list_backups()
        checkpoints = self.list_checkpoints()

        total_backup_size = sum(b['size'] for b in backups)
        total_checkpoint_size = sum(c['size'] for c in checkpoints)

        return {
            'backup_count': len(backups),
            'checkpoint_count': len(checkpoints),
            'total_backup_size': total_backup_size,
            'total_checkpoint_size': total_checkpoint_size,
            'total_size': total_backup_size + total_checkpoint_size,
            'backup_dir': str(self.backup_dir),
            'checkpoint_dir': str(self.checkpoint_dir),
        }
