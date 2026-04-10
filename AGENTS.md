# AGENTS.md

## Project Overview

`partygame` is a browser-based party game platform with:

- `frontend/`: SvelteKit app for hosting, playing, creating games, and browsing definitions
- `api/`: FastAPI backend for lobby/game state, realtime websockets, media, and game definitions
- `gateway/`: nginx reverse proxy for the containerized stack
- `valkey`: in-memory store used by the API

The main user flow is:

1. Create or define a game
2. Join a lobby from a controller device
3. Host and players connect over websocket endpoints
4. The backend advances runtime state and persists lobby/game data in Valkey

## Repository Layout

- `README.md`: top-level setup and contribution notes
- `SPEC.md`: product/spec reference
- `docker-compose.yml`: local multi-service stack
- `frontend/src/routes/`: page routes
- `frontend/src/lib/`: shared stores, websocket helpers, and UI components
- `api/partygame/api/api_v1/endpoints/`: REST and websocket endpoints
- `api/partygame/service/`: core game, lobby, player, media, and runtime logic
- `api/partygame/service/components/`: gameplay component implementations such as buzzer
- `api/partygame/state/`: persistence models and repository helpers
- `api/tests/`: backend test suite

## Local Development

### Full stack with Docker

From the repo root:

```bash
docker compose up --build
```

This starts:

- `valkey` on `6379`
- `api`
- `frontend`
- `gateway` on `http://localhost:80`

Health endpoints used by compose:

- API: `http://localhost:8000/api/health`
- Frontend: `http://localhost:3000`

### Backend

Working directory: `api/`

Install dependencies:

```bash
poetry install
```

Run the dev server:

```bash
poetry run uvicorn partygame:app --reload --reload-include "api/"
```

Useful backend checks:

```bash
poetry run pytest
poetry run ruff check .
poetry run black --check .
poetry run mypy .
```

Notes:

- The backend targets Python `3.14`.
- Websocket support depends on Uvicorn standard extras, which are already declared in `pyproject.toml`.
- The app seeds demo media from `api/media_seed/` on startup when files are present.

### Frontend

Working directory: `frontend/`

Install dependencies:

```bash
pnpm install
```

Run the dev server:

```bash
pnpm run dev -- --host
```

Useful frontend checks:

```bash
pnpm run check
pnpm run lint
pnpm run format
pnpm run build
```

Notes:

- The checked-in lockfile is `pnpm-lock.yaml`, so prefer `pnpm` over `npm`.
- The frontend uses SvelteKit 2 and Svelte 5.

## Code Quality And Hooks

This repo includes `.pre-commit-config.yaml`.

Before committing, prefer:

```bash
pre-commit run --all-files
```

Configured hooks include:

- whitespace and EOF fixes
- YAML validation
- frontend Prettier formatting via `.hooks/prettier-wrapper.sh`
- backend Black formatting
- backend Ruff linting

## Architecture Notes

### Frontend

- Route files live under `frontend/src/routes/`.
- Shared client state is managed through custom stores in `frontend/src/lib/`, including:
  - `controller-store.ts`
  - `game-store.ts`
  - `local-storage-store.ts`
  - `reconnecting-websocket.ts`
- Controller and host experiences are split across route-specific pages and component folders under `frontend/src/lib/components/`.

When editing the frontend:

- preserve existing SvelteKit routing patterns
- prefer updating shared stores/helpers when behavior is cross-cutting
- keep websocket message shapes aligned with backend schemas and runtime handlers

### Backend

- App entrypoint: `api/partygame/__init__.py`
- API router registration: `api/partygame/api/api_v1/api.py`
- Core services live in `api/partygame/service/`
- Runtime evaluation and step logic live in `api/partygame/service/runtime/`
- Persistence helpers live in `api/partygame/state/`
- Pydantic schemas live in `api/partygame/schemas/`

When editing the backend:

- keep endpoint contracts, schemas, and service-layer behavior in sync
- check whether a change belongs in `service/`, `state/`, or `schemas/` before patching endpoints directly
- add or update tests in `api/tests/` for behavior changes

## Project-Specific Guardrails

- Prefer minimal, targeted changes over broad rewrites.
- Do not replace `pnpm` commands with `npm` unless the repo is intentionally migrated.
- Do not treat `frontend/README.md` as authoritative project guidance; it is still mostly the default Svelte template.
- If you change websocket event handling, inspect both frontend stores/components and backend runtime/message handling together.
- If you change lobby/game persistence, review the repository and model files in `api/partygame/state/`.
- If you change media behavior, review both `api/partygame/service/media.py` and the seeded media setup in `api/partygame/__init__.py`.

## Suggested Workflow For Agents

1. Read `README.md` and any touched module files before editing.
2. Inspect nearby tests and existing patterns before introducing new structure.
3. Make the smallest coherent change that solves the task.
4. Run the narrowest relevant checks first, then broader validation if needed.
5. Summarize any assumptions, skipped checks, or follow-up risks in the final handoff.

## Validation Shortcuts

For typical changes, use one of these:

- Frontend UI/state changes: `cd frontend && pnpm run check && pnpm run lint`
- Frontend production readiness: `cd frontend && pnpm run build`
- Backend logic/API changes: `cd api && poetry run pytest`
- Backend quality pass: `cd api && poetry run ruff check . && poetry run black --check .`
- Cross-stack sanity check: `docker compose up --build`
