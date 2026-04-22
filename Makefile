
.PHONY: up down logs backend-test smoke

up:
	cp -n .env.example .env || true
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

backend-test:
	cd backend && pytest -q

smoke:
	curl -f http://localhost/health
	curl -f http://localhost/api/v1/docs
