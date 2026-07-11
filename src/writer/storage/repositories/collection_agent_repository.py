"""Persistence for collection-bound agent memory, runs, and proposals."""
from __future__ import annotations

import json
import hashlib
import sqlite3
import uuid
from typing import Any, Optional

from writer.domain.models.collection_agent import (
    COLLECTION_AGENT_ACTION_STATUSES,
    COLLECTION_AGENT_ACTION_TYPES,
    COLLECTION_AGENT_MEMORY_SECTIONS,
    COLLECTION_AGENT_MODES,
    COLLECTION_AGENT_RUN_STATUSES,
    COLLECTION_AGENT_STAGE_LABELS,
    AuthorPortrait,
    AuthorPortraitVersion,
    CollectionAgentAction,
    CollectionAgentDraft,
    CollectionAgentMemory,
    CollectionAgentRun,
    CollectionAgentSession,
    CollectionAgentSettings,
    CollectionAgentStyleSample,
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


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()] if isinstance(parsed, list) else []


def _row_to_settings(row: sqlite3.Row) -> CollectionAgentSettings:
    keys = row.keys()
    return CollectionAgentSettings(
        collection_id=row["collection_id"],
        profile_id=row["profile_id"] or "default",
        enabled=bool(row["enabled"]),
        active_session_id=row["active_session_id"] if "active_session_id" in keys else None,
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
    keys = row.keys()
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
        session_id=row["session_id"] if "session_id" in keys else None,
        mode=(row["mode"] if "mode" in keys else "discuss") or "discuss",
        draft_id=row["draft_id"] if "draft_id" in keys else None,
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


def _row_to_session(row: sqlite3.Row) -> CollectionAgentSession:
    return CollectionAgentSession(
        id=row["id"],
        collection_id=row["collection_id"],
        thread_id=row["thread_id"],
        title=row["title"] or "新会话",
        mode=row["mode"] or "discuss",
        summary=row["summary"] or "",
        archived=bool(row["archived"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_message_at=row["last_message_at"],
    )


def _row_to_draft(row: sqlite3.Row) -> CollectionAgentDraft:
    return CollectionAgentDraft(
        id=row["id"],
        collection_id=row["collection_id"],
        session_id=row["session_id"],
        run_id=row["run_id"],
        parent_draft_id=row["parent_draft_id"],
        title=row["title"] or "",
        content=row["content"] or "",
        brief=_json_loads(row["brief_json"]),
        variant_label=row["variant_label"] or "",
        status=row["status"] or "draft",
        target_entry_id=row["target_entry_id"],
        applied_ref_id=row["applied_ref_id"],
        content_hash=row["content_hash"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        applied_at=row["applied_at"],
    )


def _row_to_style_sample(row: sqlite3.Row) -> CollectionAgentStyleSample:
    return CollectionAgentStyleSample(
        id=row["id"],
        collection_id=row["collection_id"],
        entry_id=row["entry_id"],
        original_body=row["original_body"] or "",
        final_body=row["final_body"] or "",
        status=row["status"] or "active",
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _row_to_portrait(row: sqlite3.Row) -> AuthorPortrait:
    return AuthorPortrait(
        id=row["id"],
        tags=_json_list(row["tags_json"]),
        summary=row["summary"] or "",
        evidence_count=int(row["evidence_count"] or 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_portrait_version(row: sqlite3.Row) -> AuthorPortraitVersion:
    return AuthorPortraitVersion(
        id=row["id"],
        portrait_id=row["portrait_id"],
        tags=_json_list(row["tags_json"]),
        summary=row["summary"] or "",
        evidence_count=int(row["evidence_count"] or 0),
        reason=row["reason"] or "",
        created_at=row["created_at"],
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

    def set_active_session(
        self,
        collection_id: str,
        session_id: Optional[str],
    ) -> CollectionAgentSettings:
        self.get_settings(collection_id)
        self._conn.execute(
            """
            UPDATE collection_agent_settings
               SET active_session_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE collection_id = ?
            """,
            (session_id, collection_id),
        )
        row = self._conn.execute(
            "SELECT * FROM collection_agent_settings WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()
        assert row is not None
        return _row_to_settings(row)

    # sessions --------------------------------------------------------
    def create_session(
        self,
        collection_id: str,
        *,
        thread_id: str,
        title: str = "新会话",
        mode: str = "discuss",
    ) -> CollectionAgentSession:
        clean_mode = mode if mode in COLLECTION_AGENT_MODES else "discuss"
        session_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO collection_agent_sessions (
                id, collection_id, thread_id, title, mode
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                collection_id,
                thread_id,
                (title or "").strip()[:120] or "新会话",
                clean_mode,
            ),
        )
        loaded = self.get_session(session_id)
        assert loaded is not None
        return loaded

    def get_session(self, session_id: str) -> Optional[CollectionAgentSession]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return _row_to_session(row) if row else None

    def get_session_by_thread(self, thread_id: str) -> Optional[CollectionAgentSession]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_sessions WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        return _row_to_session(row) if row else None

    def list_sessions(
        self,
        collection_id: str,
        *,
        include_archived: bool = False,
    ) -> list[CollectionAgentSession]:
        where = "collection_id = ?"
        if not include_archived:
            where += " AND archived = 0"
        rows = self._conn.execute(
            f"""
            SELECT * FROM collection_agent_sessions
             WHERE {where}
             ORDER BY COALESCE(last_message_at, updated_at) DESC, created_at DESC
            """,
            (collection_id,),
        ).fetchall()
        return [_row_to_session(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        *,
        title: Optional[str] = None,
        mode: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> Optional[CollectionAgentSession]:
        current = self.get_session(session_id)
        if current is None:
            return None
        clean_mode = mode if mode in COLLECTION_AGENT_MODES else current.mode
        clean_title = (title if title is not None else current.title).strip()[:120] or "新会话"
        archived_value = current.archived if archived is None else bool(archived)
        self._conn.execute(
            """
            UPDATE collection_agent_sessions
               SET title = ?, mode = ?, archived = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (clean_title, clean_mode, 1 if archived_value else 0, session_id),
        )
        return self.get_session(session_id)

    def touch_session(self, session_id: str) -> None:
        self._conn.execute(
            """
            UPDATE collection_agent_sessions
               SET last_message_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (session_id,),
        )

    def save_session_summary(self, session_id: str, summary: str) -> Optional[CollectionAgentSession]:
        self._conn.execute(
            """
            UPDATE collection_agent_sessions
               SET summary = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            ((summary or "").strip(), session_id),
        )
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM collection_agent_sessions WHERE id = ?",
            (session_id,),
        )
        return cur.rowcount > 0

    def session_counts(self, session_id: str) -> dict[str, int]:
        session = self.get_session(session_id)
        if session is None:
            return {"messages": 0, "runs": 0, "drafts": 0}
        messages = self._conn.execute(
            "SELECT COUNT(*) AS n FROM ai_messages WHERE thread_id = ?",
            (session.thread_id,),
        ).fetchone()
        runs = self._conn.execute(
            "SELECT COUNT(*) AS n FROM collection_agent_runs WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        drafts = self._conn.execute(
            "SELECT COUNT(*) AS n FROM collection_agent_drafts WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return {
            "messages": int(messages["n"] if messages else 0),
            "runs": int(runs["n"] if runs else 0),
            "drafts": int(drafts["n"] if drafts else 0),
        }

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
        session_id: Optional[str] = None,
        mode: str = "discuss",
        draft_id: Optional[str] = None,
    ) -> CollectionAgentRun:
        run_id = uuid.uuid4().hex
        clean_mode = mode if mode in COLLECTION_AGENT_MODES else "discuss"
        self._conn.execute(
            """
            INSERT INTO collection_agent_runs (
                id, collection_id, thread_id, status, stage, stage_label,
                request_json, profile_id, session_id, mode, draft_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                session_id,
                clean_mode,
                draft_id,
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

    def list_runs(
        self,
        collection_id: str,
        *,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[CollectionAgentRun]:
        where = "collection_id = ?"
        params: list[Any] = [collection_id]
        if session_id:
            where += " AND session_id = ?"
            params.append(session_id)
        params.append(max(1, int(limit)))
        rows = self._conn.execute(
            f"""
            SELECT * FROM collection_agent_runs
             WHERE {where}
             ORDER BY updated_at DESC, created_at DESC
             LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_run(row) for row in rows]

    def has_active_run(self, collection_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM collection_agent_runs
             WHERE collection_id = ?
               AND status NOT IN ('succeeded', 'failed', 'cancelled')
             LIMIT 1
            """,
            (collection_id,),
        ).fetchone()
        return row is not None

    def get_active_run(self, collection_id: str) -> Optional[CollectionAgentRun]:
        row = self._conn.execute(
            """
            SELECT * FROM collection_agent_runs
             WHERE collection_id = ?
               AND status NOT IN ('succeeded', 'failed', 'cancelled')
             ORDER BY updated_at DESC LIMIT 1
            """,
            (collection_id,),
        ).fetchone()
        return _row_to_run(row) if row else None

    def has_active_run_for_session(self, session_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM collection_agent_runs
             WHERE session_id = ?
               AND status NOT IN ('succeeded', 'failed', 'cancelled')
             LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        return row is not None

    def clear_finished_runs_and_processed_actions(self, collection_id: str) -> None:
        self._conn.execute(
            """
            UPDATE collection_agent_actions
               SET run_id = NULL,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE collection_id = ?
               AND status IN ('pending', 'deferred')
            """,
            (collection_id,),
        )
        self._conn.execute(
            """
            DELETE FROM collection_agent_actions
             WHERE collection_id = ?
               AND status NOT IN ('pending', 'deferred')
            """,
            (collection_id,),
        )
        self._conn.execute(
            """
            DELETE FROM collection_agent_runs
             WHERE collection_id = ?
               AND status IN ('succeeded', 'failed', 'cancelled')
            """,
            (collection_id,),
        )

    def clear_session_history(self, collection_id: str, session_id: str) -> None:
        self._conn.execute(
            """
            UPDATE collection_agent_actions
               SET run_id = NULL,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE collection_id = ?
               AND status IN ('pending', 'deferred')
               AND run_id IN (
                   SELECT id FROM collection_agent_runs WHERE session_id = ?
               )
            """,
            (collection_id, session_id),
        )
        self._conn.execute(
            """
            DELETE FROM collection_agent_actions
             WHERE collection_id = ?
               AND status NOT IN ('pending', 'deferred')
               AND run_id IN (
                   SELECT id FROM collection_agent_runs WHERE session_id = ?
               )
            """,
            (collection_id, session_id),
        )
        self._conn.execute(
            """
            DELETE FROM collection_agent_runs
             WHERE collection_id = ? AND session_id = ?
               AND status IN ('succeeded', 'failed', 'cancelled')
            """,
            (collection_id, session_id),
        )
        self.save_session_summary(session_id, "")

    def mark_stale_runs_failed(self) -> int:
        cur = self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET status = 'failed', stage = 'failed', stage_label = ?,
                   error = '应用已重新启动，上一轮 Agent 请求不会自动重发。请确认服务商账单后再决定是否重试。',
                   completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE status NOT IN ('succeeded', 'failed', 'cancelled')
            """,
            (COLLECTION_AGENT_STAGE_LABELS["failed"],),
        )
        return cur.rowcount or 0

    def attach_draft(self, run_id: str, draft_id: str) -> Optional[CollectionAgentRun]:
        self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET draft_id = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (draft_id, run_id),
        )
        return self.get_run(run_id)

    def backfill_session_for_thread(self, thread_id: str, session_id: str) -> int:
        cur = self._conn.execute(
            """
            UPDATE collection_agent_runs
               SET session_id = ?
             WHERE thread_id = ? AND session_id IS NULL
            """,
            (session_id, thread_id),
        )
        return cur.rowcount or 0

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

    # drafts ----------------------------------------------------------
    def create_draft(
        self,
        collection_id: str,
        *,
        session_id: str,
        title: str,
        content: str,
        brief: Optional[dict[str, Any]] = None,
        run_id: Optional[str] = None,
        parent_draft_id: Optional[str] = None,
        variant_label: str = "",
    ) -> CollectionAgentDraft:
        clean_content = (content or "").strip()
        if not clean_content:
            raise ValueError("Agent 草稿内容不能为空")
        draft_id = uuid.uuid4().hex
        content_hash = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        self._conn.execute(
            """
            INSERT INTO collection_agent_drafts (
                id, collection_id, session_id, run_id, parent_draft_id,
                title, content, brief_json, variant_label, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                collection_id,
                session_id,
                run_id,
                parent_draft_id,
                (title or "").strip()[:160] or "未命名场景草稿",
                clean_content,
                _json_dumps(brief or {}),
                (variant_label or "").strip()[:80],
                content_hash,
            ),
        )
        loaded = self.get_draft(draft_id)
        assert loaded is not None
        return loaded

    def get_draft(self, draft_id: str) -> Optional[CollectionAgentDraft]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_drafts WHERE id = ?",
            (draft_id,),
        ).fetchone()
        return _row_to_draft(row) if row else None

    def list_drafts(
        self,
        collection_id: str,
        *,
        session_id: Optional[str] = None,
        include_applied: bool = True,
        limit: int = 100,
    ) -> list[CollectionAgentDraft]:
        where = "collection_id = ?"
        params: list[Any] = [collection_id]
        if session_id:
            where += " AND session_id = ?"
            params.append(session_id)
        if not include_applied:
            where += " AND status = 'draft'"
        params.append(max(1, int(limit)))
        rows = self._conn.execute(
            f"""
            SELECT * FROM collection_agent_drafts
             WHERE {where}
             ORDER BY updated_at DESC, created_at DESC
             LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_draft(row) for row in rows]

    def update_draft(
        self,
        draft_id: str,
        *,
        title: str,
        content: str,
        brief: Optional[dict[str, Any]] = None,
    ) -> Optional[CollectionAgentDraft]:
        current = self.get_draft(draft_id)
        if current is None:
            return None
        if current.status == "applied":
            raise ValueError("已应用的草稿不能继续修改")
        clean_content = (content or "").strip()
        if not clean_content:
            raise ValueError("Agent 草稿内容不能为空")
        self._conn.execute(
            """
            UPDATE collection_agent_drafts
               SET title = ?, content = ?, brief_json = ?, content_hash = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                (title or "").strip()[:160] or current.title,
                clean_content,
                _json_dumps(brief if brief is not None else current.brief),
                hashlib.sha256(clean_content.encode("utf-8")).hexdigest(),
                draft_id,
            ),
        )
        return self.get_draft(draft_id)

    def mark_draft_applied(
        self,
        draft_id: str,
        *,
        target_entry_id: str,
        applied_ref_id: str,
    ) -> Optional[CollectionAgentDraft]:
        self._conn.execute(
            """
            UPDATE collection_agent_drafts
               SET status = 'applied', target_entry_id = ?, applied_ref_id = ?,
                   applied_at = COALESCE(applied_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ? AND status = 'draft'
            """,
            (target_entry_id, applied_ref_id, draft_id),
        )
        return self.get_draft(draft_id)

    def delete_drafts(self, collection_id: str, draft_ids: list[str]) -> int:
        unique = list(dict.fromkeys(item for item in draft_ids if item))
        if not unique:
            return 0
        placeholders = ",".join("?" for _ in unique)
        cur = self._conn.execute(
            f"""
            DELETE FROM collection_agent_drafts
             WHERE collection_id = ? AND status = 'draft'
               AND id IN ({placeholders})
            """,
            (collection_id, *unique),
        )
        return cur.rowcount or 0

    def clear_unapplied_drafts(self, collection_id: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM collection_agent_drafts WHERE collection_id = ? AND status = 'draft'",
            (collection_id,),
        )
        return cur.rowcount or 0

    # author style ----------------------------------------------------
    def create_style_sample(
        self,
        collection_id: str,
        *,
        entry_id: str,
        original_body: str,
    ) -> CollectionAgentStyleSample:
        existing = self._conn.execute(
            """
            SELECT * FROM collection_agent_style_samples
             WHERE collection_id = ? AND entry_id = ? AND status = 'active'
             ORDER BY created_at DESC LIMIT 1
            """,
            (collection_id, entry_id),
        ).fetchone()
        if existing is not None:
            return _row_to_style_sample(existing)
        sample_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO collection_agent_style_samples (
                id, collection_id, entry_id, original_body
            ) VALUES (?, ?, ?, ?)
            """,
            (sample_id, collection_id, entry_id, original_body or ""),
        )
        loaded = self.get_style_sample(sample_id)
        assert loaded is not None
        return loaded

    def get_style_sample(self, sample_id: str) -> Optional[CollectionAgentStyleSample]:
        row = self._conn.execute(
            "SELECT * FROM collection_agent_style_samples WHERE id = ?",
            (sample_id,),
        ).fetchone()
        return _row_to_style_sample(row) if row else None

    def complete_style_sample(
        self,
        sample_id: str,
        *,
        final_body: str,
    ) -> Optional[CollectionAgentStyleSample]:
        self._conn.execute(
            """
            UPDATE collection_agent_style_samples
               SET final_body = ?, status = 'completed',
                   completed_at = COALESCE(completed_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
             WHERE id = ? AND status = 'active'
            """,
            (final_body or "", sample_id),
        )
        return self.get_style_sample(sample_id)

    def list_style_samples(self, collection_id: str) -> list[CollectionAgentStyleSample]:
        rows = self._conn.execute(
            """
            SELECT * FROM collection_agent_style_samples
             WHERE collection_id = ?
             ORDER BY COALESCE(completed_at, created_at) DESC
            """,
            (collection_id,),
        ).fetchall()
        return [_row_to_style_sample(row) for row in rows]

    def list_completed_style_samples(self, *, limit: int = 100) -> list[CollectionAgentStyleSample]:
        rows = self._conn.execute(
            """
            SELECT * FROM collection_agent_style_samples
             WHERE status = 'completed'
             ORDER BY completed_at DESC, created_at DESC LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
        return [_row_to_style_sample(row) for row in rows]

    def count_completed_style_samples(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM collection_agent_style_samples WHERE status = 'completed'"
        ).fetchone()
        return int(row["n"] if row else 0)

    def get_author_portrait(self, portrait_id: str = "global") -> AuthorPortrait:
        row = self._conn.execute(
            "SELECT * FROM author_portraits WHERE id = ?",
            (portrait_id,),
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO author_portraits (id) VALUES (?)",
                (portrait_id,),
            )
            row = self._conn.execute(
                "SELECT * FROM author_portraits WHERE id = ?",
                (portrait_id,),
            ).fetchone()
        assert row is not None
        return _row_to_portrait(row)

    def save_author_portrait(
        self,
        *,
        tags: list[str],
        summary: str,
        evidence_count: Optional[int] = None,
        reason: str = "manual",
        portrait_id: str = "global",
    ) -> AuthorPortrait:
        current = self.get_author_portrait(portrait_id)
        self._conn.execute(
            """
            INSERT INTO author_portrait_versions (
                id, portrait_id, tags_json, summary, evidence_count, reason
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                portrait_id,
                json.dumps(current.tags, ensure_ascii=False),
                current.summary,
                current.evidence_count,
                (reason or "").strip()[:160],
            ),
        )
        cleaned_tags = list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip()))[:24]
        resolved_evidence = current.evidence_count if evidence_count is None else max(0, int(evidence_count))
        self._conn.execute(
            """
            UPDATE author_portraits
               SET tags_json = ?, summary = ?, evidence_count = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                json.dumps(cleaned_tags, ensure_ascii=False),
                (summary or "").strip(),
                resolved_evidence,
                portrait_id,
            ),
        )
        return self.get_author_portrait(portrait_id)

    def list_author_portrait_versions(
        self,
        portrait_id: str = "global",
        *,
        limit: int = 30,
    ) -> list[AuthorPortraitVersion]:
        rows = self._conn.execute(
            """
            SELECT * FROM author_portrait_versions
             WHERE portrait_id = ?
             ORDER BY created_at DESC LIMIT ?
            """,
            (portrait_id, max(1, int(limit))),
        ).fetchall()
        return [_row_to_portrait_version(row) for row in rows]

    def restore_author_portrait_version(self, version_id: str) -> Optional[AuthorPortrait]:
        row = self._conn.execute(
            "SELECT * FROM author_portrait_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        if row is None:
            return None
        version = _row_to_portrait_version(row)
        return self.save_author_portrait(
            portrait_id=version.portrait_id,
            tags=version.tags,
            summary=version.summary,
            evidence_count=version.evidence_count,
            reason="restore",
        )

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
