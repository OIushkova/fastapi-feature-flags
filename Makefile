.PHONY : install run

-include ./.env
export

default: install

install:
	poetry install
run:
	poetry run dotenv -f .env run uvicorn --reload --host 0.0.0.0 --port 8080 src.app:app
black:
	poetry run black . --config=pyproject.toml
flake:
	poetry run flake8 --exclude=.venv --config=pyproject.toml
lint: black flake
test:
	poetry run coverage run -m --source=. pytest --junitxml=test-results/pytest/result.xml --capture=fd tests && poetry run coverage report
