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
	git push aishift master
	ssh ${PRODUCTION_HOST} 'sudo systemctl start stenographer'
