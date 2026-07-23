# Project Issues & Improvement Areas

## 1. No Tests (Critical)
- **Location**: Entire project
- Zero unit, integration, or e2e tests exist despite README claiming `pytest`.
- No test runner configured in CI.
- Core logic (claim extraction, comparison engine, graph analytics) has no coverage.

## 2. Frontend Layout Component Missing (Blocks Compilation)
- **Location**: `frontend/src/components/layout/`
- Directory is empty. `App.tsx:25` imports `Layout` from `./components/layout/Layout` — the app won't compile.
- The `feature/frontend` branch has the missing files (`Layout.tsx`, `Sidebar.tsx`, `TopBar.tsx`). A PR needs to be raised or files merged.
- Pages (Upload, Dashboard, Analysis, etc.) exist but are not fully wired to backend APIs.

## 3. Dual FastAPI Applications (Confusing Architecture)
- **Locations**: `app/main.py` and `GraphEngine/main.py`
- Two separate FastAPI apps exist, each with overlapping concerns.
- `ingestion_pipeline/main.py` imports from `GraphEngine` modules, creating circular dependency risk.
- Unclear which entry point should be used — confusing for new contributors.

## 4. Print-Based Logging
- **Location**: Throughout `ingestion_pipeline/`, `GraphEngine/`, `app/`
- Heavy use of `print()` instead of Python's `logging` module.
- No structured logging, no log levels (`INFO`, `WARN`, `ERROR`, `DEBUG`).
- Makes debugging in production difficult.

## 5. No Observability
- **Location**: Entire project
- No metrics, tracing, or APM integration.
- Only a basic `/health` endpoint exists.
- No error tracking (Sentry, Datadog, etc.).
- No request latency or throughput monitoring.

## 6. Hardcoded ChromaDB Path
- **Location**: `ingestion_pipeline/chroma_store.py:13`
- `CHROMA_DATA_DIR = os.path.join(USER_HOME, ".local_chroma_data_v12")` is hardcoded.
- Should be configurable via environment variable (e.g. `CHROMA_DB_PATH`).

## 7. No Database Migrations
- **Location**: `GraphEngine/db/models.py` and `app/core/database.py`
- Uses `Base.metadata.create_all()` on startup — no Alembic or migration tool.
- Schema changes will require manual intervention and risk data loss.

## 8. CI Lacks Quality Gates
- **Location**: `.github/` (workflows)
- No test runner in CI pipeline.
- No type checking (`mypy`, `pyright`).
- No linting enforcement (`ruff`, `flake8`).
- No security scanning (`bandit`, `safety`).

## 9. Single LLM Provider (Vendor Lock-In)
- **Location**: `GraphEngine/utils/gemini_client.py`
- All LLM calls are hardcoded to Google Gemini.
- No abstraction layer (interface/ABC) for swapping providers (OpenAI, Claude, local models via Ollama/vLLM).

## 10. Security Gaps
- **Location**: `.env.example`, `app/main.py`
- `CORS_ORIGINS=["*"]` in default config — too permissive for production.
- No rate limiting on API endpoints.
- Firebase Authentication is set up on frontend but backend API has no auth middleware — any unauthenticated request can hit endpoints.

---

## Bonus: Quick Wins

| Issue | Fix |
|---|---|
| Print → logging | Replace `print()` with `logging.getLogger(__name__)` — low effort, high impact. |
| Configurable ChromaDB path | Read `CHROMA_DB_PATH` from env with fallback to current default. |
| CORS restrict | Change default to `http://localhost:5173` for development, require env override for production. |
