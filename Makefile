.PHONY: dev-backend dev-frontend lint typecheck test build install

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

lint:
	cd backend && .venv/bin/ruff check app tests
	cd frontend && npm run lint

typecheck:
	cd frontend && npm run typecheck

test:
	cd backend && .venv/bin/python -m pytest

build:
	cd frontend && npm run build
