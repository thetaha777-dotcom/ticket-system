# BiletFlow API (FastAPI)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini docker-entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app

# Run as an ordinary user, not root. /code/media holds uploaded event images.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home appuser \
    && mkdir -p /code/media \
    && chown -R appuser /code
USER appuser

EXPOSE 8000

# The entrypoint applies database migrations (and loads demo data when SEED_DEMO_DATA=true),
# then starts the server given in CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
