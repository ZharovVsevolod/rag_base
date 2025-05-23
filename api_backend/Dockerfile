# The builder image, used to build the virtual environment
FROM python:3.12-bookworm as builder

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --extras "api" --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.12-slim-bookworm as runtime

ENV VIRTUAL_ENV=/app/.venv \
PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app

COPY data ./data
COPY bairdotr ./bairdotr
COPY api_backend/api_activation.py ./

EXPOSE 80 1702

# API
CMD python -m uvicorn api_activation:app --host 0.0.0.0 --port 1702