"""FastAPI backend server for Writer — SQLite-backed entry CRUD.

This is the single source of truth for the API. It wires the SQLite
``EntryRepository`` (see ``repository.py`` / ``database.py`` / ``models.py``)
to REST endpoints under ``/entries``, matching the frontend ``client.ts``.
"""
from __future__ import annotations

import sqlite3

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import open_and_initialize
from models import Entry, EntryCreate, EntryUpdate
from repository import EntryRepository

app = FastAPI(title="Writer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_db_conn: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        _db_conn = open_and_initialize()
    return _db_conn


def get_repository(conn: sqlite3.Connection = Depends(get_db)) -> EntryRepository:
    return EntryRepository(conn)


@app.on_event("startup")
async def startup_event() -> None:
    get_db()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _db_conn
    if _db_conn is not None:
        _db_conn.close()
        _db_conn = None


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Writer API is running", "version": "1.0.0"}


# NOTE: the static "/count" route must be declared before "/{entry_id}" so it
# is not captured by the dynamic path parameter.
@app.get("/entries/count")
async def count_entries(repo: EntryRepository = Depends(get_repository)) -> dict[str, int]:
    return {"count": repo.count()}


@app.get("/entries", response_model=list[Entry])
async def list_entries(
    limit: int = 100,
    include_archived: bool = False,
    repo: EntryRepository = Depends(get_repository),
) -> list[Entry]:
    return repo.list_recent(limit=limit, include_archived=include_archived)


@app.get("/entries/{entry_id}", response_model=Entry)
async def get_entry(
    entry_id: str,
    repo: EntryRepository = Depends(get_repository),
) -> Entry:
    entry = repo.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.post("/entries", response_model=Entry, status_code=201)
async def create_entry(
    entry_data: EntryCreate,
    repo: EntryRepository = Depends(get_repository),
) -> Entry:
    return repo.create(
        title=entry_data.title,
        body=entry_data.body,
        entry_type=entry_data.entry_type,
        tags=entry_data.tags,
    )


@app.put("/entries/{entry_id}", response_model=Entry)
async def update_entry(
    entry_id: str,
    entry_data: EntryUpdate,
    repo: EntryRepository = Depends(get_repository),
) -> Entry:
    entry = repo.update(
        entry_id,
        title=entry_data.title,
        body=entry_data.body,
        tags=entry_data.tags,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    repo: EntryRepository = Depends(get_repository),
) -> dict[str, str]:
    if not repo.delete(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted successfully"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
