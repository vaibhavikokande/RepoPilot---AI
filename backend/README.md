# RepoPilot AI — Backend

FastAPI backend service for RepoPilot AI.

## Requirements

- Python 3.10+

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values
```

## Running

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Service health check |

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/   # API endpoint handlers
│   ├── core/               # Config & constants
│   ├── models/             # Data models
│   ├── services/           # Business logic
│   ├── utils/              # Shared utilities
│   └── main.py             # Application entry point
├── tests/                  # Test suite
├── requirements.txt
└── .env.example
```
