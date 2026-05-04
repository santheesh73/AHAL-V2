test:
	python -m pytest tests/ -v

run:
	python -m app.main

docker-build:
	docker build -t ahal-ai .

docker-up:
	docker compose up --build

docker-down:
	docker compose down
