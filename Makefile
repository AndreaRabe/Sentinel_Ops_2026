.PHONY: install dev test lint migrate migration seed docker-up docker-down backup

install:
	cd backend && poetry install
	cd frontend && npm install

dev:
	docker compose -f docker-compose.dev.yml up --build

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

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

backup:
	docker compose exec postgres pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
