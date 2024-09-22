# Partygame

A browser based game controlled with clients in smartphone or computers.

Create a game, connect computer with big screen. Connect with your smartphone as a controller.

Frontend written in SvelteKit and backend in FastAPI with redis as a inmemory database.

## Development

1. Start up dependencies
   ```
   $ docker compose up -d
   ```
2. Run backend
   ```
   $ cd api
   $ poetry run uvicorn partygame:app --reload --reload-include "api/"
   ```
3. Run frontend
   ```
   $ cd frontend
   $ npm run dev -- --host
   ```

## TODO
1. GameService, GameSchema, create games, specify display component and controller component.
Look into lobby.py service `active_components`

