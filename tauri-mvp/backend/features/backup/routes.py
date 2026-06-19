"""备份和检查点 API 路由。"""
from __future__ import annotations

import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_container
from writer.app.container import AppContainer

router = APIRouter(prefix="/api/backup", tags=["backup"])


# ---- DTOs ----
class CheckpointCreate(BaseModel):
    name: str
    description: str = ""


class BackupInfo(BaseModel):
    path: str
    name: str
    size: int
    created: str


class CheckpointInfo(BaseModel):
    path: str
    name: str
    description: str
    size: int
    created: str


class BackupStats(BaseModel):
    backup_count: int
    checkpoint_count: int
    total_backup_size: int
    total_checkpoint_size: int
    total_size: int
    backup_dir: str
    checkpoint_dir: str


class RestoreRequest(BaseModel):
    backup_path: str


# ---- 自动备份 ----
@router.post("/auto-backup", response_model=BackupInfo)
def create_auto_backup(container: AppContainer = Depends(get_container)) -> BackupInfo:
    """创建自动备份。"""
    try:
        backup_path = container.backup_service.create_auto_backup()
        backups = container.backup_service.list_backups()
        backup = next((b for b in backups if b['path'] == backup_path), None)
        if not backup:
            raise HTTPException(500, "Backup created but not found in list")
        return BackupInfo(**backup)
    except Exception as e:
        raise HTTPException(500, f"Failed to create backup: {str(e)}")


@router.get("/backups", response_model=List[BackupInfo])
def list_backups(container: AppContainer = Depends(get_container)) -> List[BackupInfo]:
    """列出所有自动备份。"""
    backups = container.backup_service.list_backups()
    return [BackupInfo(**b) for b in backups]


@router.delete("/backups/{backup_name}", status_code=204)
def delete_backup(
    backup_name: str,
    container: AppContainer = Depends(get_container),
):
    """删除指定备份。"""
    backups = container.backup_service.list_backups()
    backup = next((b for b in backups if b['name'] == backup_name), None)
    if not backup:
        raise HTTPException(404, "Backup not found")

    success = container.backup_service.delete_backup(backup['path'])
    if not success:
        raise HTTPException(500, "Failed to delete backup")


# ---- 检查点 ----
@router.post("/checkpoints", response_model=CheckpointInfo, status_code=201)
def create_checkpoint(
    data: CheckpointCreate,
    container: AppContainer = Depends(get_container),
) -> CheckpointInfo:
    """创建用户检查点。"""
    try:
        checkpoint_path = container.backup_service.create_checkpoint(
            name=data.name,
            description=data.description,
        )
        checkpoints = container.backup_service.list_checkpoints()
        checkpoint = next((c for c in checkpoints if c['path'] == checkpoint_path), None)
        if not checkpoint:
            raise HTTPException(500, "Checkpoint created but not found in list")
        return CheckpointInfo(**checkpoint)
    except Exception as e:
        raise HTTPException(500, f"Failed to create checkpoint: {str(e)}")


@router.get("/checkpoints", response_model=List[CheckpointInfo])
def list_checkpoints(
    container: AppContainer = Depends(get_container),
) -> List[CheckpointInfo]:
    """列出所有检查点。"""
    checkpoints = container.backup_service.list_checkpoints()
    return [CheckpointInfo(**c) for c in checkpoints]


@router.delete("/checkpoints/{checkpoint_name}", status_code=204)
def delete_checkpoint(
    checkpoint_name: str,
    container: AppContainer = Depends(get_container),
):
    """删除指定检查点。"""
    checkpoints = container.backup_service.list_checkpoints()
    # 支持通过 name 或完整路径匹配
    checkpoint = next(
        (c for c in checkpoints if checkpoint_name in c['path'] or c['name'] == checkpoint_name),
        None
    )
    if not checkpoint:
        raise HTTPException(404, "Checkpoint not found")

    success = container.backup_service.delete_checkpoint(checkpoint['path'])
    if not success:
        raise HTTPException(500, "Failed to delete checkpoint")


# ---- 恢复 ----
@router.post("/restore", status_code=200)
def restore_from_backup(
    data: RestoreRequest,
    container: AppContainer = Depends(get_container),
):
    """从备份或检查点恢复数据库。

    警告：这会替换当前数据库！会先创建当前数据库的备份。
    """
    try:
        try:
            container.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        container.close()
        try:
            success = container.backup_service.restore_from_backup(data.backup_path)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not success:
            raise HTTPException(500, "Failed to restore from backup")
    finally:
        get_container.cache_clear()
    return {"message": "Database restored successfully"}


# ---- 统计 ----
@router.get("/stats", response_model=BackupStats)
def get_backup_stats(
    container: AppContainer = Depends(get_container),
) -> BackupStats:
    """获取备份统计信息。"""
    stats = container.backup_service.get_backup_stats()
    return BackupStats(**stats)
