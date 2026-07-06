"""Persistence for collection-bound agent memory, runs, and proposals."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Optional

from writer.domain.models.collection_agent import (
    COLLECTION_AGENT_ACTION_STATUSES,
    COLLECTION_AGENT_ACTION_TYPES,
    COLLECTION_AGENT_MEMORY_SECTIONS,
    COLLECTION_AGENT_RUN_STATUSES,
    COLLECTION_AGENT_STAGE_LABELS,
    CollectionAgentAction,
    CollectionAgentMemory,
    CollectionAgentRun,
    CollectionAgentSettings,
)


def default_agent_memory_sections() -> dict[str, str]:
    return {section_id: "" for section_id, _title, _help in COLLECTION_AGENT_MEMORY_SECTIONS}


def normalize_agent_memory(value: Any) -> dict[str, str]:
    defaults = default_agent_memory_sections()
    if not isinstance(value, dict):
        return defaults
    normalized = defaults.copy()
    raw_sections = value.get("sections") if "sections" in value else value
    if not isinstance(raw_sections, dict):
        return normalized
    for key in normalized:
        raw = raw_sections.get(key, "")
        if isinstance(raw, list):
            normalized[key] = "\n".join(str(item).strip() for item in raw if str(item).strip())
        else:
            normalized[key] = str(raw or "").strip()
    return normalized


def _json_dumps(value: Any) -> str:
    if value is None:
        value = {}
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _row_to_settings(row: sqlite3.Row) -> CollectionAgentSettings:
    return CollectionAgentSettings(
        collection_id=row["collection_id"],
        profile_id=row["profile_id"] or "default",
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_memory(row: sqlite3.Row) -> CollectionAgentMemory:
    return CollectionAgentMemory(
        collection_id=row["collection_id"],
        sections=normalize_agent_memory(_json_loads(row["memory_json"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_run(row: sqlite3.Row) -> CollectionAgentRun:
    return CollectionAgentRun(
        id=row["id"],
        collection_id=row["collection_id"],
        thread_id=row["thread_id"],
        user_message_id=row["user_message_id"],
        assistant_message_id=row["assistant_message_id"],
        status=row["status"],
        stage=row["stage"],
        stage_label=row["stage_label"],
        request=_json_loads(row["request_json"]),
        result=_json_loads(row["result_json"]),
        error=row["error"] or "",
        profile_id=row["profile_id"] or "default",
        provider=row["provider"],
        model=row["model"],
        transport=row["transport"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


def _row_to_action(row: sqlite3.Row) -> CollectionAgentAction:
    return CollectionAgentAction(
        id=row["id"],
        collection_id=row["collection_id"],
        run_id=row["run_id"],
        action_type=row["action_type"],
        status=row["status"],
        title=row["title"] or "",
        summary=row["summary"] or "",
        payload=_json_loads(row["payload_json"]),
        preview=_json_loads(row["preview_json"]),
        reason=row["reason"] or "",
        risk=row["risk"] or "",
        applied_ref_id=row["applied_ref_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        applied_at=row["applied_at"],
    )


class CollectionAgentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # settings ---------------------------------------------------------
    def get_settings(self, collection_id: str) -> CollectionAgentSettings:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_settings WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()
        if row is not None:
            return _row_to_settings(row)
        return self.save_settings(collection_id, profile_id="default", enabled=True)

    def save_settings(
        self,
        collection_id: str,
        *,
        profile_id: str = "default",
        enabled: bool = True,
    ) -> CollectionAgentSettings:
        clean_profile = (profile_id or "default").strip() or "default"
        self._conn.execute(
            """
            INSERT INTO collection_agent_settings (collection_id, profile_id, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(collection_id) DO UPDATE SET
                profile_id = excluded.profile_id,
                enabled = excluded.enabled,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (collection_id, clean_profile, 1 if enabled else 0),
        )
        row = self._conn.execute(
            "SELECT * FROM collection_agent_settings WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()
        assert row is not None
        return _row_to_settings(row)

    # memory -----------------------------------------------------------
    def get_memory(self, collection_id: str) -> CollectionAgentMemory:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_memory WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()
        if row is not None:
            return _row_to_memory(row)
        return self.save_memory(collection_id, default_agent_memory_sections())

    def save_memory(self, collection_id: str, sections: dict[str, Any]) -> CollectionAgentMemory:
        normalized = normalize_agent_memory(sections)
        self._conn.execute(
            """
            INSERT INTO collection_agent_memory (collection_id, memory_json)
            VALUES (?, ?)
            ON CONFLICT(collection_id) DO UPDATE SET
                memory_json = excluded.memory_json,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (collection_id, _json_dumps({"sections": normalized})),
        )
        row = self._conn.execute(
            "SELECT * FROM collection_agent_memory WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()
        assert row is not None
        return _row_to_memory(row)

    def update_memory_section(
        self,
        collection_id: str,
        section_id: str,
        content: str,
        *,
        mode: str = "replace",
    ) -> CollectionAgentMemory:
        memory = self.get_memory(collection_id)
        sections = memory.sections.copy()
        if section_id not in sections:
            raise ValueError("Unknown agent memory section")
        clean_content = (content or "").strip()
        if mode == "append" and sections[section_id].strip():
            if clean_content and clean_content not in sections[section_id]:
                sections[section_id] = f"{sections[section_id].strip()}\n\n{clean_content}"
        else:
            sections[section_id] = clean_content
        return self.save_memory(collection_id, sections)

    # runs -------------------------------------------------------------
    def create_run(
        self,
        collection_id: str,
        *,
        thread_id: Optional[str],
        profile_id: str,
        request: dict[str, Any],
    ) -> CollectionAgentRun:
        run_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO collection_agent_runs (
                id, collection_id, thread_id, status, stage, stage_label,
                request_json, profile_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                collection_id,
                thread_id,
                "queued",
                "queued",
                COLLECTION_AGENT_STAGE_LABELS["queued"],
                _json_dumps(request),
                (profile_id or "default").strip() or "default",
            ),
        )
        loaded = self.get_run(run_id)
        assert loaded is not None
        return loaded

    def get_run(self, run_id: str) -> Optional[CollectionAgentRun]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return _row_to_run(row) if row else None

    def list_runs(self, collection_id: str, *, limit: int = 20) -> list[CollectionAgentRun]:
        rows = self._conn.execute(
            """
            SELECT * FROM collection_agent_runs
             WHERE collection_id = ?
             ORDER BY updated_at DESC, created_at DESC
             LIMIT ?
            """,
            (collection_id, max(1, int(limit))),
        ).fetchall()
        return [_row_to_run(row) for row in rows]

    def mark_run_started(self, run_id: str) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = 'preparing_context',
                   stage = 'preparing_context',
                   stage_label = ?,
                   started_at = COALESCE(started_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (COLLECTION_AGENT_STAGE_LABELS["preparing_context"], run_id),
        )
        return self.get_run(run_id)

    def update_run_stage(self, run_id: str, stage: str) -> Optional[CollectionAgentRun]:
        clean_stage = stage if stage in COLLECTION_AGENT_RUN_STATUSES else "preparing_context"
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = ?,
                   stage = ?,
                   stage_label = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ? AND status NOT IN ('succeeded', 'failed', 'cancelled')
            """,
            (
                clean_stage,
                clean_stage,
                COLLECTION_AGENT_STAGE_LABELS.get(clean_stage, clean_stage),
                run_id,
            ),
        )
        return self.get_run(run_id)

    def complete_run(
        self,
        run_id: str,
        *,
        result: dict[str, Any],
        assistant_message_id: Optional[str],
        provider: Optional[str],
        model: Optional[str],
        transport: Optional[str],
    ) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = 'succeeded',
                   stage = 'succeeded',
                   stage_label = ?,
                   result_json = ?,
                   error = '',
                   assistant_message_id = ?,
                   provider = ?,
                   model = ?,
                   transport = ?,
                   completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ? AND status != 'cancelled'
            """,
            (
                COLLECTION_AGENT_STAGE_LABELS["succeeded"],
                _json_dumps(result),
                assistant_message_id,
                provider,
                model,
                transport,
                run_id,
            ),
        )
        return self.get_run(run_id)

    def fail_run(self, run_id: str, error: str) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = 'failed',
                   stage = 'failed',
                   stage_label = ?,
                   error = ?,
                   completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ? AND status != 'cancelled'
            """,
            (COLLECTION_AGENT_STAGE_LABELS["failed"], (error or "").strip(), run_id),
        )
        return self.get_run(run_id)

    def cancel_run(self, run_id: str) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = 'cancelled',
                   stage = 'cancelled',
                   stage_label = ?,
                   error = '已停止本地等待。若请求已经发给服务商，远端仍可能完成并计费。',
                   completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ? AND status NOT IN ('succeeded', 'failed', 'cancelled')
            """,
            (COLLECTION_AGENT_STAGE_LABELS["cancelled"], run_id),
        )
        return self.get_run(run_id)

    def attach_user_message(self, run_id: str, message_id: str) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET user_message_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (message_id, run_id),
        )
        return self.get_run(run_id)

    # actions ----------------------------------------------------------
    def create_action(
        self,
        collection_id: str,
        *,
        run_id: Optional[str],
        action_type: str,
        title: str,
        summary: str = "",
        payload: Optional[dict[str, Any]] = None,
        preview: Optional[dict[str, Any]] = None,
        reason: str = "",
        risk: str = "",
    ) -> CollectionAgentAction:
        clean_type = (action_type or "").strip()
        if clean_type not in COLLECTION_AGENT_ACTION_TYPES:
            raise ValueError("Unsupported collection agent action type")
        action_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO collection_agent_actions (
                id, collection_id, run_id, action_type, title, summary,
                payload_json, preview_json, reason, risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                collection_id,
                run_id,
                clean_type,
                (title or "").strip() or "Agent 提案",
                summary or "",
                _json_dumps(payload or {}),
                _json_dumps(preview or {}),
                reason or "",
                risk or "",
            ),
        )
        loaded = self.get_action(action_id)
        assert loaded is not None
        return loaded

    def get_action(self, action_id: str) -> Optional[CollectionAgentAction]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_actions WHERE id = ?",
            (action_id,),
        ).fetchone()
        return _row_to_action(row) if row else None

    def list_actions(
        self,
        collection_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[CollectionAgentAction]:
        params: list[Any] = [collection_id]
        where = "collection_id = ?"
        if status:
            where += " AND status = ?"
            params.append(status)
        params.append(max(1, int(limit)))
        rows = self._conn.execute(
            f"""
            SELECT * FROM collection_agent_actions
             WHERE {where}
             ORDER BY updated_at DESC, created_at DESC
             LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_action(row) for row in rows]

    def set_action_status(
        self,
        action_id: str,
        status: str,
        *,
        applied_ref_id: Optional[str] = None,
    ) -> Optional[CollectionAgentAction]:
        clean_status = (status or "").strip()
        if clean_status not in COLLECTION_AGENT_ACTION_STATUSES:
            raise ValueError("Unsupported collection agent action status")
        applied_expr = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')" if clean_status == "applied" else "applied_at"
        self._conn.execute(
            f"""
            UPDATE collection_agent_actions
               SET status = ?,
                   applied_ref_id = COALESCE(?, applied_ref_id),
                   applied_at = {applied_expr},
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (clean_status, applied_ref_id, action_id),
        )
        return self.get_action(action_id)
