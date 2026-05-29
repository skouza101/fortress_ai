web: prisma generate && prisma db push --skip-generate && uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.worker.celery_app worker --concurrency=1 --loglevel=info
