# Ani-CLI FastAPI

A FastAPI application for searching and streaming anime using the AllAnime provider via anipy_api.

## Project Structure

```
ani-cli/
├── main.py                 # Main entry point
├── app/                    # Application package
│   ├── __init__.py        # FastAPI app factory
│   ├── config.py          # Configuration settings
│   ├── models.py          # Pydantic models
│   ├── utils.py           # Utility functions
│   └── routes/            # API route handlers
│       ├── __init__.py
│       ├── root.py        # Root and health endpoints
│       ├── search.py      # Search endpoints
│       ├── anime.py       # Anime info and episodes
│       └── stream.py      # Streaming endpoints
├── anipy_api/             # External API library
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
└── README.md
```

## Setup

### Requirements
- Python 3.10+
- Virtual Environment

### Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

### FastAPI Server

Start the FastAPI server:

```bash
source .venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

### Development Server

For development with auto-reload:

```bash
source .venv/bin/activate
python3 main.py
```

## API Endpoints

### Root
- `GET /` - API information and available endpoints

### Health Check
- `GET /health` - Server health status

### Search
- `GET /search?query={anime_name}&limit={limit}` - Search for anime
  - Parameters:
    - `query` (required): Anime name to search
    - `limit` (optional): Max results (1-50, default: 10)

### Anime Info
- `GET /anime/{identifier}` - Get detailed anime information
  - Parameters:
    - `identifier`: Anime ID from search results

### Episodes
- `GET /anime/{identifier}/episodes?language={language}` - Get available episodes
  - Parameters:
    - `identifier`: Anime ID
    - `language` (optional): Filter by language (sub/dub)

### Streams
- `GET /anime/{identifier}/episode/{episode}/stream?language={language}` - Get streaming links
  - Parameters:
    - `identifier`: Anime ID
    - `episode`: Episode number
    - `language`: Language (sub/dub)

## Example Usage

### Search for anime
```bash
curl "http://localhost:8000/search?query=Naruto&limit=5"
```

Response:
```json
{
  "query": "Naruto",
  "total_results": 28,
  "results": [
    {
      "name": "Naruto",
      "identifier": "cstcbG4EquLyDnAwN",
      "languages": ["sub", "dub"]
    },
    ...
  ]
}
```

### Get anime info
```bash
curl "http://localhost:8000/anime/cstcbG4EquLyDnAwN"
```

### Get streams for an episode
```bash
curl "http://localhost:8000/anime/cstcbG4EquLyDnAwN/episode/1/stream?language=sub"
```

## Interactive Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Both provide interactive ways to explore and test all available endpoints.

## Files

- `app.py` - FastAPI application
- `main.py` - CLI test script for anipy_api
- `requirements.txt` - Python dependencies
- `test_api.py` - API endpoint testing script
- `.venv/` - Python virtual environment

## Troubleshooting

### Import errors
If you get import errors, make sure the virtual environment is activated:
```bash
source .venv/bin/activate
```

### Port already in use
Change the port in the uvicorn command:
```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001
```

### SSL/Certificate errors
SSL verification is disabled by default for development. To enable it, remove the `provider.session.verify = False` line in `app.py`.

## Project Structure

```
ani-cli/
├── app.py                    # FastAPI application
├── main.py                   # CLI test script
├── test_api.py              # API test script
├── requirements.txt         # Dependencies
├── .venv/                   # Virtual environment
└── anipy_api/              # Anime API library
    ├── anime.py
    ├── provider/
    │   ├── base.py
    │   ├── providers/
    │   │   ├── allanime_provider.py
    │   │   ├── animekai_provider.py
    │   │   └── native_provider.py
    │   └── utils.py
    └── ...
```

## License

This is a wrapper around the anipy-api library for educational purposes.
