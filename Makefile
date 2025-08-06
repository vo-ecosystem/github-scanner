.PHONY: build run clean

build:
	docker-compose build

run:
	docker-compose run --rm github-scanner

scan: build run

clean:
	docker-compose down
	rm -rf reports/*.json

logs:
	docker-compose logs -f
