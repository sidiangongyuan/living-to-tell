# Living to Tell Backend API

FastAPI backend for the Tauri preview of 活着为了讲述 / Living to Tell.

The backend wraps the shared Python `writer` package and exposes HTTP endpoints for the Vue/Tauri frontend.

## Setup

```powershell
pip install -r requirements.txt
```

## Run in development

Use an isolated development database:

```powershell
$env:WRITER_USE_DEV_DB = "1"
python run.py --dev
```

The server starts at `http://127.0.0.1:8000` by default.

## API documentation

When the server is running:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Data location

Production Tauri builds use the branded local data directory:

```text
%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3
```

On first launch, the app copies old Writer data from:

```text
%APPDATA%\Writer\Writer\writer.sqlite3
```

The old database is retained and is not deleted by migration.
