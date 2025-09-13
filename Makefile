# Makefile
.PHONY: test test-models test-coverage test-fast install-test-deps test-setup freeze-requirements

# Install test dependencies
install-test-deps:
	pip install pytest pytest-cov pytest-asyncio factory-boy faker

# Run all model tests
test-models:
	python -m pytest tests/unit/test_data/test_models/ -v

# Run model tests with coverage
test-coverage:
	python -m pytest tests/unit/test_data/test_models/ --cov=app.data.models --cov-report=html --cov-report=term-missing

# Run all tests (excluding /eval)
test:
	python -m pytest tests/ -v --ignore=tests/evals

# Run fast tests (unit only, also exclude /eval just in case)
test-fast:
	python -m pytest tests/unit/ -v --disable-warnings --ignore=tests/evals

run-evals:
	python -u tests/evals/run_eval.py

run-local:
	@echo "Starting local development environment..."
	docker-compose up --build -d
	@echo "Services started! Open chat_tester.html in your browser to test the system."
	@echo "Or visit: file://$(PWD)/chat_tester.html"

run-local-with-chat:
	@echo "Starting local development environment..."
	docker-compose up --build -d
	@sleep 3
	@echo "Opening chat interface..."
	@( \
		(command -v open >/dev/null 2>&1 && open local_run/chat_tester.html) || \
		(command -v xdg-open >/dev/null 2>&1 && xdg-open local_run/chat_tester.html) || \
		(command -v cmd >/dev/null 2>&1 && cmd /c start local_run/chat_tester.html) || \
		(command -v powershell >/dev/null 2>&1 && powershell -Command "Start-Process 'local_run/chat_tester.html'") || \
		echo "✅ Services started! Please manually open local_run/chat_tester.html in your browser" \
	) 2>/dev/null || echo "✅ Services started! Please manually open local_run/chat_tester.html in your browser"
	@echo "💡 Direct file path: file://$(PWD)/local_run/chat_tester.html"

# Update requirements.txt with currently installed packages
freeze-req:
	pip freeze > requirements.txt
