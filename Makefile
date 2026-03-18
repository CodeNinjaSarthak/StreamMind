.PHONY: help run-backend run-workers format lint test test-coverage install clean migrate migration downgrade db-init

help:
	@echo "AI Live Doubt Manager - Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make run-backend       - Start FastAPI backend server"
	@echo "  make run-workers       - Start background workers"
	@echo "  make format            - Format code with black and isort"
	@echo "  make lint              - Run linters (ruff, flake8, pylint)"
	@echo "  make test              - Run tests"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo ""
	@echo "Database:"
	@echo "  make db-init           - Initialize database and create tables"
	@echo "  make migrate           - Run database migrations"
	@echo "  make migration MSG=... - Create new migration"
	@echo "  make downgrade         - Rollback last migration"
	@echo ""
	@echo "Setup:"
	@echo "  make install           - Install dependencies"
	@echo "  make clean             - Clean generated files"

run-backend:
	cd backend && PYTHONPATH=$(CURDIR) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-workers:
	python -m workers.runner

format:
	black backend workers scripts --line-length 119
	isort backend workers scripts --profile black --line-length 119

lint:
	ruff check backend workers scripts
	flake8 backend workers scripts --max-line-length=119 --ignore=D107,D212,E501,W503,W605,D203,D100 \
		--per-file-ignores="backend/alembic/*:E402,F401 backend/app/main.py:E402,F824 backend/app/db/models/migrations/*:W391 workers/*/worker.py:E402,F824 workers/*/mock_worker.py:E402,F824 workers/runner.py:E402 scripts/*:E402,E226"
	pylint backend workers scripts \
		--ignore-paths="backend/alembic/versions/" \
		--disable=line-too-long,trailing-whitespace,missing-function-docstring,missing-module-docstring,missing-class-docstring,consider-using-f-string,import-error,too-few-public-methods,redefined-outer-name,wrong-import-position,wrong-import-order,ungrouped-imports,invalid-name,logging-fstring-interpolation,global-statement,global-variable-not-assigned,unnecessary-pass,fixme,pointless-string-statement,broad-exception-caught,duplicate-code,too-many-locals,too-many-arguments,too-many-branches,too-many-statements,too-many-nested-blocks,too-many-instance-attributes,unused-argument,unused-import,unused-variable,no-member,import-outside-toplevel,raise-missing-from,not-callable,singleton-comparison,no-else-continue,implicit-str-concat,keyword-arg-before-vararg,missing-timeout,subprocess-run-check,protected-access

test:
	pytest backend/tests workers -v

test-coverage:
	pytest backend/tests workers --cov=backend --cov=workers --cov-report=html --cov-report=term

install:
	pip install -r backend/requirements.txt
	pip install -r workers/requirements.txt

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +

db-init:
	cd backend && python -c "from app.db.session import init_db; init_db()"

migrate:
	cd backend && alembic upgrade head

migration:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG is required. Usage: make migration MSG='description'"; \
		exit 1; \
	fi
	cd backend && alembic revision --autogenerate -m "$(MSG)"

downgrade:
	cd backend && alembic downgrade -1

