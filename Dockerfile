FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry>=2.2,<3"

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root --no-ansi

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY --chown=app:app . .

RUN mkdir -p /app/staticfiles /app/beat-data \
    && chown app:app /app/staticfiles /app/beat-data

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]