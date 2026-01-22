# Testing Documentation

This project maintains a comprehensive test suite using `pytest`, achieving **99% code coverage**.

## Test Structure

- **`tests/test_clients.py`**: Tests `GitHubClient`.
  - Mocks `httpx` to simulate GitHub API responses.
  - Verifies pagination logic and error handling (404, rate limits).
- **`tests/test_llm_client.py`**: Tests `LLMProvider` logic.
  - Verifies dynamic provider selection (OpenAI, Anthropic, Gemini, Mock).
  - Tests "Map-Reduce" chunking logic for large contexts.
  - Ensures graceful error handling for all providers.
- **`tests/test_database.py`**: Tests SQLite interactions.
  - Uses a temporary database fixture to ensure isolation.
  - Verifies CRUD operations (Upsert, Get, Delete) and idempotency.
- **`tests/test_main.py`**: Tests FastAPI endpoints (`/scan`, `/analyze`).
  - Mocks external services (GitHub, LLM) to test API logic in isolation.
  - Verifies background tasks (stale issue pruning).

## Running Tests

Prerequisites:
```bash
pip install -r requirements.txt
```

Run all tests:
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```

## Current Coverage

| File | Coverage | Notes |
|Data | --- | --- |
| `clients.py` | 96% | Minor unreachable error path |
| `database.py` | 100% | Full CRUD coverage |
| `llm_client.py` | 100% | All providers and chunking logic |
| `main.py` | 98% | Startup/Lifespan logic covered |
| **Total** | **99%** | Robust validation |

## Rationale
We prioritized high coverage to ensure reliability in a production-like environment. Mocks are used extensively to avoid dependency on external APIs during testing, ensuring tests are fast and deterministic.
