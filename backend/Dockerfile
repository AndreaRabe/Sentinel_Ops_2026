FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false

FROM base AS dev
RUN poetry install --no-root
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload"]

FROM base AS prod
RUN poetry install --no-root --without dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
