# Partygame

Partygame is a browser-based party game platform for playing quiz and host-led games on a shared screen while players join from their phones or laptops.

The project is built for the classic living-room, classroom, or event setup:

- one main screen shows the game
- one person can act as a host and control the flow
- players join from their own devices as controllers

Game definitions, realtime lobby state, and controller interactions are handled across a SvelteKit frontend and a FastAPI backend. Postgres stores editable game definitions, while Valkey is used for in-memory lobby/runtime state.

## Overview

Partygame lets you:

- create or define a game
- open a lobby for players to join
- run the game on a big screen
- let players answer from their own devices
- support both host-driven and automatically evaluated gameplay

The platform is designed around realtime party-game interactions such as:

- buzzer rounds
- text or number answers
- ordering tasks
- media-based prompts with images, audio, or video

## Project Structure

- `frontend/`: SvelteKit app for hosting, playing, creating games, and browsing definitions
- `api/`: FastAPI backend for lobby state, game flow, websockets, and media
- `gateway/`: nginx reverse proxy used in the containerized stack
- `docker-compose.yml`: local development stack
- `SPEC.md`: product and gameplay reference

## Quick Start

If you want to run the whole stack locally, the easiest path is Docker Compose:

```bash
docker compose up --build
```

This starts:

- `valkey` on port `6379`
- `postgres` on port `5432`
- the API service
- the frontend service
- the gateway on `http://localhost:80`

Useful health endpoints:

- API: `http://localhost:8000/api/health`
- Frontend: `http://localhost:3000`

## Local Development

### Backend

From [`api/`](/home/jaagup/theority/partygame/api):

```bash
poetry install
poetry run alembic upgrade head
poetry run uvicorn partygame:app
```

Built-in definitions from `api/games/*.json` are seed data. On startup the API imports any missing definitions into Postgres without overwriting database-edited definitions.

Useful checks:

```bash
poetry run pytest
poetry run ruff check .
poetry run black --check .
poetry run mypy .
```

### Frontend

From [`frontend/`](/home/jaagup/theority/partygame/frontend):

```bash
pnpm install
pnpm run dev -- --host
```

Useful checks:

```bash
pnpm run check
pnpm run lint
pnpm run build
```

## Contributing

Contributions are welcome. If you are making changes, aim for small, focused updates and check nearby code and tests before introducing new structure.

This repository uses `pre-commit` hooks to help keep formatting and linting consistent.

Install and enable them with:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Configured hooks include:

- whitespace and end-of-file fixes
- YAML validation
- frontend formatting via Prettier
- backend formatting with Black
- backend linting with Ruff

## Notes

- Prefer `pnpm` for frontend work because the repo uses `pnpm-lock.yaml`
- The backend targets Python `3.14`
- Demo media can be seeded from `api/media_seed/` when files are present

For more implementation details and workflow expectations, see [`AGENTS.md`](/home/jaagup/theority/partygame/AGENTS.md)
