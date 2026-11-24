set -e

echo "Applying database migrations..."
alembic upgrade head

if [ "$SEED_DEMO_DATA" = "true" ]; then
  echo "Loading demo data (skipped automatically when the database already has users)..."
  python -m app.seed
fi

exec "$@"
