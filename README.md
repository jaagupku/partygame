# Mänguõhtu

Mänguõhtu is a browser-based platform for hosted quizzes, trivia nights, and casual party games on a shared screen while players join from their phones or laptops. Games can run with a dedicated host or without one, so everyone can play.

Public site: [game.theority.ee](https://game.theority.ee).

The project is built for the classic living-room, classroom, or event setup:

- one main screen shows the game
- one person can act as a host and control the flow
- players join from their own devices as controllers

Game definitions, realtime lobby state, and controller interactions are handled across a SvelteKit frontend and a FastAPI backend. Postgres stores editable game definitions, while Valkey is used for in-memory lobby/runtime state.

## Overview

Mänguõhtu lets you:

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

With Docker and Docker Compose installed, start the whole development stack from the repository root:

```bash
docker compose up --build
```

This starts:

- `valkey` on port `6379`
- `postgres` on port `5432`
- the API with Uvicorn automatic reload, after applying database migrations
- the frontend with Vite hot module replacement
- the gateway on `http://localhost:80`

Open **http://localhost**. The development admin login is `admin@example.com` / `admin123` (seeded on first startup). These credentials are for local development only.

Source edits are mounted into the containers: Svelte, TypeScript, and CSS updates appear in the browser, and Python changes restart the API. Polling is enabled for Docker Desktop and WSL compatibility. No host Node, pnpm, Python, or Poetry installation is needed. Dependencies and generated files stay inside the containers.

Use `DEV_PORT=8080 docker compose up --build` to serve the gateway on a different port. PostgreSQL and Valkey also require host ports 5432 and 6379 to be free.

Press Ctrl+C to stop. `docker compose down` removes the containers but preserves PostgreSQL data and uploaded media; `docker compose down -v` deletes that saved development data. Active lobby state in Valkey is disposable.

After changing dependency manifests or lockfiles, rerun `docker compose up --build`. After adding a database migration, run `docker compose restart api`; migrations run before the API starts. Built-in game definitions are seed data: changes do not overwrite definitions already edited in the database.

Run checks inside the running containers:

```bash
docker compose exec frontend pnpm run check
docker compose exec frontend pnpm run lint
docker compose exec frontend pnpm run test
docker compose exec api poetry run pytest
docker compose exec api poetry run ruff check .
docker compose exec api poetry run black --check .
```

Compose selects the `development` Dockerfile targets. Plain `docker build ./frontend` and `docker build ./api` still produce production images. Production deployments should use those images, not this development Compose configuration.

Health endpoints through the gateway are `http://localhost/api/health` and `http://localhost`. Inside the Compose network, health checks use API port 8000 and frontend port 3000; those ports are not published to the host.

## Local Development

### Backend

From [`api/`](/home/jaagup/theority/partygame/api):

```bash
poetry install
poetry run alembic upgrade head
poetry run uvicorn partygame:app --reload --reload-dir partygame
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
pnpm run dev --host
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

See [Adding games](docs/game-sessions.md) for the game catalog, frozen sessions,
round composition, and future dataset generators.

[Price Guessing](docs/price-game.md) documents the playable modes, weekly product
refresh, dataset migration, scheduler service, and validation.
