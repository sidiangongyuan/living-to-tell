# Writer — Tauri MVP

A from-scratch rebuild of Writer's shell on **Tauri 2 + Vue 3 + Tailwind**, backed by
**FastAPI + SQLite**. This MVP exists to prove the layout that the Qt/PySide6 build
could not get right: a three-column shell where toggling the right context pane
**reflows the center column** instead of pushing the pane off-screen.

## Why this rebuild

The Qt version drove splitter sizes with manual width math (`setSizes`,
`minimumSizeHint`, deferred normalize). Across 9 fixes it still let the context
pane render off-screen on maximize+toggle, because Qt enforces child minimum
widths by stealing pixels from the rightmost pane.

Here the shell is plain CSS flexbox:

- left rail — `w-20 shrink-0`
- center (list + editor) — `flex-1 min-w-0` (the only column that shrinks)
- right context pane — `w-72 shrink-0`, shown/hidden with `v-show`

There is **no width arithmetic anywhere**. The browser's layout engine reflows
the center column when the pane appears or disappears, so the off-screen bug is
structurally impossible.

## Architecture

```
frontend/  Tauri 2 + Vue 3 + Vite + Tailwind
  src/App.vue          three-column shell, list/editor/context, debounced autosave
  src/api/client.ts    typed fetch wrapper for the backend
  src-tauri/           Tauri shell (Rust)

backend/   FastAPI + SQLite
  server.py            /entries CRUD (list, get, create, update, delete, count)
  repository.py        EntryRepository — SQLite access
  database.py          connection + idempotent schema (WAL, FK on)
  models.py            Pydantic Entry / EntryCreate / EntryUpdate
```

Frontend talks to the backend over HTTP at `http://127.0.0.1:8000`
(override with `VITE_API_BASE_URL`).

## Run it (development)

Two processes. **Backend** first:

```bash
cd backend
"D:/anaconda/envs/writer/python.exe" -m pip install -r requirements.txt   # first time
"D:/anaconda/envs/writer/python.exe" server.py
# serves http://127.0.0.1:8000  (docs at /docs)
```

**Frontend** (browser dev, fastest iteration):

```bash
cd frontend
npm install        # first time
npm run dev
# open http://localhost:1420
```

**Frontend (native Tauri window):**

```bash
cd frontend
npm run tauri:dev
```

## Verify

```bash
cd frontend && npm run build      # vue-tsc type-check + vite bundle
```

Backend CRUD was verified end-to-end (create → list → get → update → delete → 404).

## MVP scope

- [x] Three-column shell + context-pane toggle (reflow, no off-screen bug)
- [x] Article list with selection
- [x] Editor (title + body) with debounced autosave
- [x] Create / delete
- [x] Live word / char / line counts
- [x] SQLite persistence via FastAPI
- [ ] Tauri sidecar packaging (bundle the Python backend into the app)
- [ ] Port the rest of the Qt features (collections, AI, reference library)
