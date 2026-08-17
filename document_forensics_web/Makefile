.PHONY: dev test up down logs

dev:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8080

test:
	pytest -q

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f
