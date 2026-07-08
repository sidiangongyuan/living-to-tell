"""In-process AI background job manager.

Jobs are intentionally process-local. They keep long provider calls alive while
the frontend closes a dialog or reconnects status polling, without persisting
private AI results to disk.
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from threading import Lock
from typing import Any, Callable, Optional

from fastapi import HTTPException


AI_JOB_STAGES = {
    "queued": "排队中",
    "preparing_context": "整理上下文",
    "sending_request": "发送请求",
    "waiting_model": "已发送请求，等待模型返回",
    "parsing_response": "正在解析结构化结果",
    "succeeded": "已完成",
    "failed": "失败",
    "cancelled": "已中断",
}
AI_JOB_KIND_STAGE_LABELS = {
    "motif_enrichment": {
        "preparing_context": "整理当前意象资料",
        "parsing_response": "正在解析结构化草稿",
    },
    "ai_card_draft": {
        "preparing_context": "整理卡片材料",
        "parsing_response": "正在解析卡片草稿",
    },
}
AI_JOB_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
AI_JOB_RETENTION_SECONDS = 30 * 60

StageUpdater = Callable[[str], None]
JobWorker = Callable[[StageUpdater], Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage_label(kind: str, stage: str) -> str:
    return AI_JOB_KIND_STAGE_LABELS.get(kind, {}).get(stage) or AI_JOB_STAGES.get(stage, stage)


def _safe_job_error(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "AI 后台任务失败，请稍后重试。"
    lowered = raw.lower()
    if "<!doctype html" in lowered or "<html" in lowered:
        return "AI 服务返回了网页错误页，请检查接口协议、模型权限和密钥。"
    if "traceback" in lowered:
        return "AI 后台任务失败，后台返回了异常信息。请检查模型配置后重试。"
    raw = re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-***", raw)
    return raw[:400].rstrip() + ("..." if len(raw) > 400 else "")


@dataclass
class AiJobRecord:
    job_id: str
    kind: str
    concept: str
    motif_id: Optional[str]
    profile_id: str
    status: str = "queued"
    stage: str = "queued"
    stage_label: str = AI_JOB_STAGES["queued"]
    result: Any = None
    error: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    transport: Optional[str] = None
    created_at: str = ""
    started_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    started_monotonic: Optional[float] = None
    completed_monotonic: Optional[float] = None
    cancel_requested: bool = False

    def elapsed_ms(self) -> int:
        if self.started_monotonic is None:
            return 0
        end = self.completed_monotonic if self.completed_monotonic is not None else time.perf_counter()
        return max(0, int((end - self.started_monotonic) * 1000))


class AiJobManager:
    def __init__(self, *, max_workers: int = 4, retention_seconds: int = AI_JOB_RETENTION_SECONDS) -> None:
        self._lock = Lock()
        self._jobs: dict[str, AiJobRecord] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._retention_seconds = retention_seconds

    def create(
        self,
        *,
        kind: str,
        concept: str,
        motif_id: Optional[str],
        profile_id: str,
        worker: JobWorker,
    ) -> AiJobRecord:
        self._cleanup()
        now = _now_iso()
        record = AiJobRecord(
            job_id=uuid.uuid4().hex,
            kind=kind,
            concept=concept,
            motif_id=motif_id,
            profile_id=profile_id,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[record.job_id] = record
        self._executor.submit(self._run, record.job_id, worker)
        return self.get(record.job_id)

    def get(self, job_id: str) -> AiJobRecord:
        self._cleanup()
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise HTTPException(404, "后台任务已不存在，可能是应用重启或任务已过期。")
            return self._copy(record)

    def cancel(self, job_id: str) -> AiJobRecord:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise HTTPException(404, "后台任务已不存在，可能是应用重启或任务已过期。")
            if record.status not in AI_JOB_TERMINAL_STATUSES:
                record.cancel_requested = True
                record.status = "cancelled"
                record.stage = "cancelled"
                record.stage_label = _stage_label(record.kind, "cancelled")
                record.error = "已停止本地等待。若请求已经发给服务商，远端仍可能完成并计费。"
                record.updated_at = _now_iso()
                record.completed_at = record.updated_at
                record.completed_monotonic = time.perf_counter()
            return self._copy(record)

    def update_stage(self, job_id: str, stage: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None or record.status in AI_JOB_TERMINAL_STATUSES:
                return
            record.status = stage
            record.stage = stage
            record.stage_label = _stage_label(record.kind, stage)
            record.updated_at = _now_iso()

    def complete(self, job_id: str, result: Any) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None or record.status == "cancelled" or record.cancel_requested:
                return
            record.status = "succeeded"
            record.stage = "succeeded"
            record.stage_label = _stage_label(record.kind, "succeeded")
            record.result = result
            record.error = ""
            record.provider = getattr(result, "provider", None)
            record.model = getattr(result, "model", None)
            record.transport = getattr(result, "transport", None)
            record.updated_at = _now_iso()
            record.completed_at = record.updated_at
            record.completed_monotonic = time.perf_counter()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None or record.status == "cancelled" or record.cancel_requested:
                return
            record.status = "failed"
            record.stage = "failed"
            record.stage_label = _stage_label(record.kind, "failed")
            record.error = error
            record.updated_at = _now_iso()
            record.completed_at = record.updated_at
            record.completed_monotonic = time.perf_counter()

    def _run(self, job_id: str, worker: JobWorker) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None or record.cancel_requested:
                return
            record.started_at = _now_iso()
            record.started_monotonic = time.perf_counter()
            record.updated_at = record.started_at
        try:
            result = worker(lambda stage: self.update_stage(job_id, stage))
        except HTTPException as exc:
            self.fail(job_id, _safe_job_error(exc.detail))
        except Exception as exc:  # noqa: BLE001
            self.fail(job_id, _safe_job_error(exc))
            return
        self.complete(job_id, result)

    def _cleanup(self) -> None:
        cutoff = time.perf_counter() - self._retention_seconds
        with self._lock:
            expired = [
                job_id
                for job_id, record in self._jobs.items()
                if record.status in AI_JOB_TERMINAL_STATUSES
                and record.completed_monotonic is not None
                and record.completed_monotonic < cutoff
            ]
            for job_id in expired:
                self._jobs.pop(job_id, None)

    @staticmethod
    def _copy(record: AiJobRecord) -> AiJobRecord:
        return AiJobRecord(**record.__dict__)


ai_job_manager = AiJobManager()
