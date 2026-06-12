# Writer Backend API

FastAPI backend for the Writer application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

The server will start at `http://localhost:8000`

## API Endpoints

### Base
- `GET /` - Root endpoint with API info

### Entries
- `GET /entries` - List recent entries
  - Query params: `limit` (default: 100), `include_archived` (default: false)
- `GET /entries/{entry_id}` - Get a single entry by ID
- `POST /entries` - Create a new entry
  - Body: `{"title": str, "body": str, "entry_type": str, "tags": list[str]}`
- `PUT /entries/{entry_id}` - Update an entry
  - Body: `{"title": str, "body": str, "tags": list[str]}`
- `DELETE /entries/{entry_id}` - Delete an entry
- `GET /entries/count` - Get total entry count

## API Documentation

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database

The backend uses SQLite with the database file `writer.db` created in the backend directory.
