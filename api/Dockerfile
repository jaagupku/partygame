FROM python:3.14 AS builder

# Install Poetry using the official installer (recommended for CI)
ENV POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PATH="$POETRY_HOME/bin:$PATH"

# Ensure curl is available so the Poetry installer can be fetched
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - && /opt/poetry/bin/poetry --version && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.14-slim AS runtime
RUN apt-get -y update && \
    apt-get -y install curl && \
    rm -rf /var/lib/apt/lists/*
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY partygame ./partygame

CMD ["uvicorn", "partygame:app", "--host", "0.0.0.0", "--port", "8000"]
