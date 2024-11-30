# The builder image, used to build the virtual environment
FROM python:3.11-buster as builder

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --extras "telegram" --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.11-slim-buster as runtime

ENV VIRTUAL_ENV=/app/.venv \
PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app

RUN apt-get update
RUN apt-get install -y ffmpeg

COPY data ./data
COPY aurora ./aurora
COPY .env ./
COPY telegram_backend/telegram_chat.py ./
COPY telegram_backend/utils ./utils

EXPOSE 80

# Telegram bot
ENTRYPOINT ["python", "-m", "telegram_chat"]