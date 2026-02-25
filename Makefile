.PHONY: build run clean rebuild pretty dbr dpr

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

# Delete orphaned branches (branches without open PRs)
dbr: build
	@echo "⚠️  WARNING: This will DELETE all orphaned branches!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	UID=$$(id -u) GID=$$(id -g) docker compose run --rm github-scanner --delete-branches

# Delete (close) stale PRs that exceed the threshold
dpr: build
	@echo "⚠️  WARNING: This will CLOSE all stale PRs exceeding the threshold!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	UID=$$(id -u) GID=$$(id -g) docker compose run --rm github-scanner --delete-prs

clean:
	docker compose down
	rm -rf reports/

logs:
	docker compose logs -f

# Force rebuild and run
fresh: rebuild run
