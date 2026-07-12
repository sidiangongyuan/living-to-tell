"""Process-local article AI task runs.

The provider calls live in worker threads so navigation or closing the AI view
does not abort paid work. Runs are deliberately not persisted: a full app
restart clears private prompts and results.
"""
from __future__ import annotations

import copy
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable, Optional

from fastapi import HTTPException
from features.ai.error_messages import friendly_ai_error


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
STAGE_LABELS = {
    "queued": "排队中",
    "preparing_context": "整理文章与要求",
    "sending_request": "正在发送请求",
    "waiting_model": "已发送请求，等待模型返回",
    "collecting_results": "正在收集模型结果",
    "succeeded": "已完成",
    "failed": "失败",
    "cancelled": "已中断本地等待",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_error(value: Any) -> str:
    return friendly_ai_error(value)


@dataclass
class ArticleTaskRunRecord:
    run_id: str
    article_id: str
    article_title: str
    task_type: str
    article_hash: str
    article_body: str
    target_text: str
    selection_start: Optional[int]
    selection_end: Optional[int]
    request: dict[str, Any]
    profiles: list[dict[str, Any]]
    results: list[dict[str, Any]]
    status: str = "queued"
    stage: str = "queued"
    stage_label: str = STAGE_LABELS["queued"]
    error: str = ""
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=_now_iso)
    completed_at: Optional[str] = None
    started_monotonic: Optional[float] = None
    completed_monotonic: Optional[float] = None
    cancel_requested: bool = False
    applied_profile_id: Optional[str] = None
    applied_at: Optional[str] = None
    applied_version_id: Optional[str] = None
    applied_entry: Optional[dict[str, Any]] = None

    def elapsed_ms(self) -> int:
        if self.started_monotonic is None:
            return 0
        end = self.completed_monotonic or time.perf_counter()
        return max(0, int((end - self.started_monotonic) * 1000))


RunWorker = Callable[[str], None]


class ArticleTaskRunManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, ArticleTaskRunRecord] = {}
        self._latest_run_id: Optional[str] = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def create(self, record: ArticleTaskRunRecord, worker: RunWorker) -> ArticleTaskRunRecord:
        with self._lock:
            active = next(
                (item for item in self._runs.values() if item.status not in TERMINAL_STATUSES),
                None,
            )
            if active is not None:
                raise HTTPException(409, "已有文章 AI 任务正在运行，请等待完成或先中断本地等待。")
            if not record.run_id:
                record.run_id = uuid.uuid4().hex
            self._runs[record.run_id] = record
            self._latest_run_id = record.run_id
        self._executor.submit(self._run, record.run_id, worker)
        return self.get(record.run_id)

    def _run(self, run_id: str, worker: RunWorker) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None or record.cancel_requested:
                return
            record.status = "running"
            record.stage = "preparing_context"
            record.stage_label = STAGE_LABELS[record.stage]
            record.started_at = _now_iso()
            record.updated_at = record.started_at
            record.started_monotonic = time.perf_counter()
        try:
            worker(run_id)
        except Exception as exc:  # noqa: BLE001
            self.fail(run_id, str(exc))

    def get(self, run_id: str) -> ArticleTaskRunRecord:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise HTTPException(404, "文章 AI 任务已不存在，可能是应用已经重启或结果已清空。")
            return copy.deepcopy(record)

    def latest(self) -> Optional[ArticleTaskRunRecord]:
        with self._lock:
            if not self._latest_run_id:
                return None
            record = self._runs.get(self._latest_run_id)
            return copy.deepcopy(record) if record is not None else None

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            record = self._runs.get(run_id)
            return record is None or record.cancel_requested or record.status == "cancelled"

    def set_stage(self, run_id: str, stage: str) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None or record.status in TERMINAL_STATUSES:
                return
            record.stage = stage
            record.stage_label = STAGE_LABELS.get(stage, stage)
            record.updated_at = _now_iso()

    def set_result(self, run_id: str, profile_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None or record.cancel_requested or record.status == "cancelled":
                return
            for index, existing in enumerate(record.results):
                if str(existing.get("profile_id") or "") == profile_id:
                    record.results[index] = copy.deepcopy(result)
                    break
            record.stage = "collecting_results"
            record.stage_label = STAGE_LABELS[record.stage]
            record.updated_at = _now_iso()

    def complete(self, run_id: str) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None or record.cancel_requested or record.status == "cancelled":
                return
            record.status = "succeeded"
            record.stage = "succeeded"
            record.stage_label = STAGE_LABELS[record.stage]
            record.updated_at = _now_iso()
            record.completed_at = record.updated_at
            record.completed_monotonic = time.perf_counter()

    def fail(self, run_id: str, error: str) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None or record.cancel_requested or record.status == "cancelled":
                return
            record.status = "failed"
            record.stage = "failed"
            record.stage_label = STAGE_LABELS[record.stage]
            record.error = _safe_error(error)
            record.updated_at = _now_iso()
            record.completed_at = record.updated_at
            record.completed_monotonic = time.perf_counter()

    def cancel(self, run_id: str) -> ArticleTaskRunRecord:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise HTTPException(404, "文章 AI 任务已不存在，可能是应用已经重启或结果已清空。")
            if record.status not in TERMINAL_STATUSES:
                record.cancel_requested = True
                record.status = "cancelled"
                record.stage = "cancelled"
                record.stage_label = STAGE_LABELS[record.stage]
                record.error = "已停止本地等待。已发出的远端请求仍可能继续生成并计费。"
                record.updated_at = _now_iso()
                record.completed_at = record.updated_at
                record.completed_monotonic = time.perf_counter()
            return copy.deepcopy(record)

    def mark_applied(
        self,
        run_id: str,
        *,
        profile_id: str,
        version_id: str,
        entry: dict[str, Any],
    ) -> ArticleTaskRunRecord:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise HTTPException(404, "文章 AI 任务已不存在，可能是应用已经重启或结果已清空。")
            record.applied_profile_id = profile_id
            record.applied_version_id = version_id
            record.applied_entry = copy.deepcopy(entry)
            record.applied_at = _now_iso()
            record.updated_at = record.applied_at
            return copy.deepcopy(record)

    def delete(self, run_id: str) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise HTTPException(404, "文章 AI 任务已不存在，可能是应用已经重启或结果已清空。")
            if record.status not in TERMINAL_STATUSES:
                raise HTTPException(400, "运行中的任务不能清空，请先等待完成或中断本地等待。")
            self._runs.pop(run_id, None)
            if self._latest_run_id == run_id:
                self._latest_run_id = None


article_task_run_manager = ArticleTaskRunManager()
