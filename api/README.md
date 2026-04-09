# Patrygame API

Backend api that handles Websockets and games.

Run development server with

Make sure the install includes Uvicorn's standard extras so WebSocket support is available.

```
$ poetry run uvicorn partygame:app --reload --reload-include "api/"
```
