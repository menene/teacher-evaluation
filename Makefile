.PHONY: up down build logs ps shell-backend shell-db restart

## Start all services (detached)
up:
	docker compose up -d

## Start all services with logs in foreground
up-watch:
	docker compose up

## Stop all services
down:
	docker compose down

## Stop and remove volumes (wipes database!)
down-volumes:
	docker compose down -v

## Rebuild images and start
build:
	docker compose up -d --build

## Show running containers
ps:
	docker compose ps

## Tail all logs
logs:
	docker compose logs -f

## Tail backend logs only
logs-backend:
	docker compose logs -f backend

## Open a shell inside the backend container
shell-backend:
	docker compose exec backend bash

## Open a MariaDB shell
shell-db:
	docker compose exec db mariadb -u $${DB_USER} -p$${DB_PASSWORD} $${DB_NAME}

## Restart a single service  (make restart svc=backend)
restart:
	docker compose restart $(svc)
