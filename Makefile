-include .env
.PHONY: format lint install run deploy

run:
	uv run main.py

format:
	uv run ruff format

lint: format
	uv run ruff check --fix
	uv run mypy .

install:
	./install.sh

deploy:
	ssh ${PRODUCTION_HOST} 'sudo systemctl stop stenographer'
	rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' ./ ${PRODUCTION_HOST}:/home/stenographer/stenographer/
	ssh ${PRODUCTION_HOST} 'cd /home/stenographer/stenographer && ~/.local/bin/uv python pin 3.12 && ~/.local/bin/uv sync'
	ssh ${PRODUCTION_HOST} 'sudo systemctl start stenographer'
