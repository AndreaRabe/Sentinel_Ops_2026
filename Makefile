.PHONY: install dev test lint migrate migration seed backup

install:
	cd backend && poetry install
	cd frontend && npm install

# Lance backend (uvicorn --reload) et frontend (Vite) en parallele.
# Necessite PostgreSQL deja demarre en local (voir README).
dev:
	@trap 'kill 0' EXIT; \
	(cd backend && poetry run uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

test:
	cd backend && poetry run pytest
	cd frontend && npm run test

lint:
	cd backend && poetry run ruff check . && poetry run black --check .
	cd frontend && npm run lint

migrate:
	cd backend && poetry run alembic upgrade head

migration:
	cd backend && poetry run alembic revision --autogenerate -m "$(name)"

seed:
	cd backend && poetry run python -m app.db.seed

backup:
	set -a && . ./.env && set +a && mkdir -p backups && \
	pg_dump -U $$POSTGRES_USER -h localhost $$POSTGRES_DB > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
