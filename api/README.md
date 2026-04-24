# Patrygame API

Backend api that handles Websockets and games.

Run development server with

Make sure the install includes Uvicorn's standard extras so WebSocket support is available.
Run database migrations before starting the API when running outside Docker Compose.

```
$ poetry run alembic upgrade head
$ poetry run uvicorn partygame:app --reload --reload-include "api/"
```

Game definitions are stored in Postgres. The JSON files in `games/` are imported as missing seed definitions on API startup and are not treated as the runtime source of truth.
