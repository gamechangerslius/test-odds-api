### OpticOdds Soccer Opportunities API

Small FastAPI service that integrates with the OpticOdds Odds API to expose normalized upcoming soccer betting opportunities.

It focuses on a single endpoint:

- `GET /v1/opportunities` — returns normalized soccer opportunities (moneyline by default) with optional filtering and simple pagination.

---

### Project structure

- `app/main.py` — FastAPI application entrypoint and router wiring
- `app/core/config.py` — configuration and settings (API key, defaults)
- `app/core/logging_config.py` — basic structured logging setup
- `app/clients/base.py` — abstract odds client interface
- `app/clients/exceptions.py` — shared provider client error types
- `app/clients/opticodds.py` — async OpticOdds HTTP client (fixtures + odds)
- `app/services/base.py` — abstract opportunities service interface
- `app/services/opticodds_opportunities.py` — OpticOdds-backed opportunities service (normalization + filtering)
- `app/schemas/opportunity.py` — Pydantic response models
- `app/api/dependencies.py` — FastAPI dependencies wiring the client + service
- `app/api/routes/opportunities.py` — `GET /v1/opportunities` route
- `requirements.txt` — Python dependencies

---

### Installation

1. **Create and activate a virtualenv (recommended):**

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

---

### Configuration and API key

The service reads configuration from environment variables (optionally via a `.env` file in the project root).

- **Required:**
  - `OPTICODDS_API_KEY` — your OpticOdds API key

- **Optional (sensible defaults are provided):**
  - `OPTICODDS_BASE_URL` — base URL for the API (defaults to `https://api.opticodds.com/api/v3`)
  - `DEFAULT_SPORT` — sport identifier (defaults to `soccer`)
  - `DEFAULT_MARKET` — market identifier (defaults to `moneyline`)
  - `DEFAULT_SPORTSBOOKS` — comma-separated sportsbooks list (defaults to `DraftKings`)

Example `.env` file:

```env
OPTICODDS_API_KEY=your_real_key_here
```

You can also export `OPTICODDS_API_KEY` directly in your shell instead of using `.env`.

---

### Running the service

From the project root:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

- Health check: `GET /health`
- Opportunities: `GET /v1/opportunities`

---

### Endpoint: `GET /v1/opportunities`

Returns normalized upcoming soccer betting opportunities.

**Query parameters:**

- `league` (optional) — filter by league name, e.g. `England - Premier League`.
- `sportsbook` (optional) — sportsbook filter as a string:
  - Single: `DraftKings`
  - Multiple (comma-separated): `DraftKings,BetMGM`
- `market` (optional) — market filter as a string:
  - Single: `moneyline`
  - Multiple (comma-separated): `moneyline,total_goals`
- `page` (optional, default `1`) — fixture page number forwarded to OpticOdds `/fixtures/active?page=...`.

Sportsbook and market filtering is applied after normalization; the OpticOdds odds request will only constrain by `market` when you provide a value.

**Example request:**

```bash
curl "http://localhost:8000/v1/opportunities?league=England%20-%20Premier%20League&market=moneyline&sportsbook=DraftKings,BetMGM&page=1"
```

**Example response shape:**

```json
{
  "results": [
    {
      "event_id": "20250318ABCDE",
      "match": "Arsenal vs Chelsea",
      "league": "Premier League",
      "sport": "soccer",
      "start_time": "2026-03-18T18:00:00Z",
      "sportsbook": "DraftKings",
      "market": "moneyline",
      "selection": "Arsenal",
      "line": null,
      "odds": -120
    }
  ]
}
```

Notes:

- Only fixtures with a valid ISO-8601 start time and valid odds are included.
- Each object in `results` represents a single betting opportunity (fixture + selection).
- Results are scoped to a single fixtures page (via `page`), and odds requests are automatically chunked (up to ~20 fixtures per call) to keep upstream requests reasonable.

---

### Error handling

The service aims to fail cleanly:

- **Upstream provider unavailable / network issues:**
  - Returns `502 Bad Gateway` with a generic message.
- **Bad or unexpected provider response shape:**
  - Returns `502 Bad Gateway`.
- **Unexpected internal error:**
  - Returns `500 Internal Server Error`.
- **Empty result set:**
  - Returns `200 OK` with `"results": []`.

Normalization guards against missing or malformed fields; problematic odds entries or fixtures are skipped and logged rather than crashing the request.

---

### Logging

Logging is kept small but useful:

- Provider calls log:
  - start, success, and failure for fixtures and odds requests
- Normalization logs:
  - missing IDs, invalid start times, missing team names, or malformed odds entries
- Endpoint logs:
  - request parameters and number of opportunities returned

Logs are written to stdout in a simple, structured format suitable for local development and containerized environments.

