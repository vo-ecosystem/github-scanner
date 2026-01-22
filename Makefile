.PHONY: build run clean rebuild pretty

build:
	docker compose build --build-arg USER_ID=$$(id -u) --build-arg GROUP_ID=$$(id -g)

rebuild:
	docker compose build --no-cache  --build-arg USER_ID=$$(id -u) --build-arg GROUP_ID=$$(id -g)

run:
	UID=$$(id -u) GID=$$(id -g) docker compose run --rm github-scanner

scan: build run

# Run with pretty table output
pretty: build
	UID=$$(id -u) GID=$$(id -g) docker compose run --rm github-scanner --pretty

clean:
	docker compose down
	rm -rf reports/

logs:
	docker compose logs -f

# Force rebuild and run
fresh: rebuild run
