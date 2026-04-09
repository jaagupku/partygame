# Partygame

A browser based game controlled with clients in smartphone or computers.

Create a game, connect computer with big screen. Connect with your smartphone as a controller.

Frontend written in SvelteKit and backend in FastAPI with Valkey as the in-memory data store.

## Contributing

### Pre-commit Hooks

This project uses pre-commit hooks to maintain code quality. The hooks automatically run before each commit to:

- Ensure files end with a newline
- Remove trailing whitespace
- Format frontend code with Prettier
- Format backend Python code with Black
- Lint Python code with Ruff
- Validate YAML files

#### Setup

1. Install pre-commit:
   ```
   $ pip install pre-commit
   ```

2. Install the git hooks:
   ```
   $ pre-commit install
   ```

3. (Optional) Run hooks on all files to check the current state:
   ```
   $ pre-commit run --all-files
   ```

The hooks will now run automatically on every commit.

## Development

1. Start up dependencies
   ```
   $ docker compose up -d
   ```
   This starts Valkey on port `6379` for the backend.
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
