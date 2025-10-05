# Makefile
.PHONY: test test-models test-coverage test-fast install-test-deps test-setup freeze-requirements help install install-dev freeze requirements update-requirements clean

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Directory paths
FLASK_DIR := .  # Flask run.py is in root directory
REACT_DIR := ./web-client  # React app folder

# Default target - show help
help:
	@echo "$(GREEN)Available commands:$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker Development:$(NC)"
	@echo "  start-docker                        - Start all services in Docker (backend, frontend, db, redis)"
	@echo "  stop-docker                         - Stop all Docker services"
	@echo "  restart-docker                      - Restart all Docker services"
	@echo "  logs-backend                        - View backend logs"
	@echo "  logs-frontend                       - View frontend logs"
	@echo "  logs-all                            - View all service logs"
	@echo "  docker-build                        - Rebuild Docker images"
	@echo "  docker-clean                        - Remove all containers and volumes"
	@echo ""
	@echo "$(YELLOW)Local Development (without Docker):$(NC)"
	@echo "  start-backend                       - Start Flask backend server locally"
	@echo "  start-frontend                      - Start React frontend server locally"
	@echo "  start-both                          - Start both Flask and React servers locally"
	@echo "  stop-servers                        - Stop both local servers"
	@echo ""
	@echo "$(YELLOW)Legacy Docker:$(NC)"
	@echo "  run-local                           - Start local development environment (Docker)"
	@echo "  run-local-with-chat                 - Start local environment and open chat interface"
	@echo ""
	@echo "$(YELLOW)Testing:$(NC)"
	@echo "  test                                - Run all tests (excluding /eval)"
	@echo "  test-fast                           - Run fast unit tests only"
	@echo "  test-models                         - Run model tests"
	@echo "  test-coverage                       - Run model tests with coverage"
	@echo "  run-evals                           - Run evaluations"
	@echo "  install-test-deps                   - Install test dependencies"
	@echo ""
	@echo "$(YELLOW)Package Management:$(NC)"
	@echo "  install PACKAGE=<package>           - Install a package and update requirements.txt"
	@echo "  install-dev PACKAGE=<package>       - Install a dev package and update requirements-dev.txt"
	@echo "  freeze-req                          - Generate requirements.txt from current environment"
	@echo "  requirements                        - Install all packages from requirements.txt"
	@echo "  update-requirements                 - Update all packages and regenerate requirements.txt"
	@echo "  uninstall PACKAGE=<package>         - Uninstall a package and update requirements.txt"
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@echo "  clean                               - Clean up cache files"
	@echo "  show-versions                       - Show current package versions"
	@echo "  show-outdated                       - Show outdated packages"
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make install PACKAGE=anthropic"
	@echo "  make install PACKAGE=\"anthropic==0.25.0\""
	@echo "  make uninstall PACKAGE=some-package"
	@echo "  make start-both                     - Start both servers"

# === DOCKER DEVELOPMENT COMMANDS ===

# Start all Docker services
start-docker:
	@echo "$(GREEN)Starting all Docker services...$(NC)"
	docker-compose up --build -d
	@echo "$(GREEN)✅ All services started!$(NC)"
	@echo "$(YELLOW)Backend:  http://localhost:5000$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:5173$(NC)"
	@echo "$(YELLOW)Postgres: localhost:5432$(NC)"
	@echo "$(YELLOW)Redis:    localhost:6379$(NC)"
	@echo ""
	@echo "$(YELLOW)View logs: make logs-all$(NC)"

# Stop all Docker services
stop-docker:
	@echo "$(GREEN)Stopping all Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ All services stopped$(NC)"

# Restart all Docker services
restart-docker:
	@echo "$(GREEN)Restarting all Docker services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✅ All services restarted$(NC)"

# View backend logs
logs-backend:
	@echo "$(GREEN)Showing backend logs (Ctrl+C to exit)...$(NC)"
	docker-compose logs -f backend

# View frontend logs
logs-frontend:
	@echo "$(GREEN)Showing frontend logs (Ctrl+C to exit)...$(NC)"
	docker-compose logs -f frontend

# View all service logs
logs-all:
	@echo "$(GREEN)Showing all logs (Ctrl+C to exit)...$(NC)"
	docker-compose logs -f

# Rebuild Docker images
docker-build:
	@echo "$(GREEN)Rebuilding Docker images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✅ Docker images rebuilt$(NC)"

# Clean up Docker containers and volumes
docker-clean:
	@echo "$(RED)⚠️  This will remove all containers and volumes!$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or wait 5 seconds to continue...$(NC)"
	@sleep 5
	docker-compose down -v
	@echo "$(GREEN)✅ Docker containers and volumes removed$(NC)"

# === LOCAL DEVELOPMENT COMMANDS (without Docker) ===

run-local:
	@echo "$(GREEN)Starting local development environment...$(NC)"
	docker-compose up --build -d
	@echo "$(GREEN)Services started! Open chat_tester.html in your browser to test the system.$(NC)"
	@echo "$(YELLOW)Or visit: file://$(PWD)/chat_tester.html$(NC)"

run-local-with-chat:
	@echo "$(GREEN)Starting local development environment...$(NC)"
	docker-compose up --build -d
	@sleep 3
	@echo "$(GREEN)Opening chat interface...$(NC)"
	@-open local_run/chat_tester.html 2>/dev/null || \
	 xdg-open local_run/chat_tester.html 2>/dev/null || \
	 cmd /c start local_run/chat_tester.html 2>/dev/null || \
	 powershell -Command "Start-Process 'local_run/chat_tester.html'" 2>/dev/null || \
	 echo "$(YELLOW)⚠️  Auto-open failed - please open manually$(NC)"
	@echo "$(GREEN)✅ Services started!$(NC)"
	@echo "$(YELLOW)💡 Direct file path: file://$(PWD)/local_run/chat_tester.html$(NC)"

# Start Flask backend server
start-backend:
	@echo "$(GREEN)Starting Flask backend server...$(NC)"
	@if [ -f "run.py" ]; then \
		python run.py & \
		echo $! > .backend.pid; \
		echo "$(GREEN)✅ Flask backend started on http://localhost:5000$(NC)"; \
		echo "$(YELLOW)PID: $(cat .backend.pid)$(NC)"; \
	else \
		echo "$(RED)Error: run.py not found in current directory$(NC)"; \
		exit 1; \
	fi

# Start React frontend server
start-frontend:
	@echo "$(GREEN)Starting React frontend server...$(NC)"
	@if [ -d "$(REACT_DIR)" ]; then \
		cd $(REACT_DIR) && npm run dev & \
		echo $$! > .frontend.pid; \
		sleep 2; \
		echo "$(GREEN)✅ React frontend started on http://localhost:5173$(NC)"; \
		echo "$(YELLOW)PID: $$(cat $(REACT_DIR)/.frontend.pid)$(NC)"; \
	else \
		echo "$(RED)Error: React directory '$(REACT_DIR)' not found$(NC)"; \
		exit 1; \
	fi

# Start both servers
start-both:
	@echo "$(GREEN)Starting both Flask and React servers...$(NC)"
	@$(MAKE) start-backend
	@sleep 2
	@$(MAKE) start-frontend
	@echo ""
	@echo "$(GREEN)=====================================$(NC)"
	@echo "$(GREEN)✅ Both servers are running!$(NC)"
	@echo "$(GREEN)=====================================$(NC)"
	@echo "$(YELLOW)Backend:  http://localhost:5000$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:5173$(NC)"
	@echo ""
	@echo "$(YELLOW)To stop servers, run: make stop-servers$(NC)"

# Stop both servers
stop-servers:
	@echo "$(GREEN)Stopping servers...$(NC)"
	@if [ -f ".backend.pid" ]; then \
		kill $(cat .backend.pid) 2>/dev/null || true; \
		rm .backend.pid; \
		echo "$(GREEN)✅ Flask backend stopped$(NC)"; \
	else \
		echo "$(YELLOW)No Flask backend PID file found$(NC)"; \
	fi
	@if [ -f "$(REACT_DIR)/.frontend.pid" ]; then \
		kill $(cat $(REACT_DIR)/.frontend.pid) 2>/dev/null || true; \
		rm $(REACT_DIR)/.frontend.pid; \
		echo "$(GREEN)✅ React frontend stopped$(NC)"; \
	else \
		echo "$(YELLOW)No React frontend PID file found$(NC)"; \
	fi
	@pkill -f "vite" 2>/dev/null || true
	@pkill -f "python run.py" 2>/dev/null || true
	@echo "$(GREEN)All servers stopped$(NC)"

# === TESTING COMMANDS ===

# Install test dependencies
install-test-deps:
	@echo "$(GREEN)Installing test dependencies...$(NC)"
	pip install pytest pytest-cov pytest-asyncio factory-boy faker
	@echo "$(GREEN)✅ Test dependencies installed$(NC)"

# Run all model tests
test-models:
	@echo "$(GREEN)Running model tests...$(NC)"
	python -m pytest tests/unit/test_data/test_models/ -v

# Run model tests with coverage
test-coverage:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	python -m pytest tests/unit/test_data/test_models/ --cov=app.data.models --cov-report=html --cov-report=term-missing

# Run all tests (excluding /eval)
test:
	@echo "$(GREEN)Running all tests...$(NC)"
	python -m pytest tests/ -v --ignore=tests/evals

# Run fast tests (unit only, also exclude /eval just in case)
test-fast:
	@echo "$(GREEN)Running fast unit tests...$(NC)"
	python -m pytest tests/unit/ -v --disable-warnings --ignore=tests/evals

run-evals:
	@echo "$(GREEN)Running evaluations...$(NC)"
	python -u tests/evals/run_eval.py

# === PACKAGE MANAGEMENT COMMANDS ===

# Install a package and update requirements.txt
install:
ifndef PACKAGE
	@echo "$(RED)Error: PACKAGE variable is required$(NC)"
	@echo "Usage: make install PACKAGE=<package_name>"
	@exit 1
endif
	@echo "$(GREEN)Installing $(PACKAGE)...$(NC)"
	pip install $(PACKAGE)
	@echo "$(GREEN)Updating requirements.txt...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✅ Package $(PACKAGE) installed and requirements.txt updated$(NC)"

# Install a dev package and update requirements-dev.txt
install-dev:
ifndef PACKAGE
	@echo "$(RED)Error: PACKAGE variable is required$(NC)"
	@echo "Usage: make install-dev PACKAGE=<package_name>"
	@exit 1
endif
	@echo "$(GREEN)Installing dev package $(PACKAGE)...$(NC)"
	pip install $(PACKAGE)
	@echo "$(GREEN)Updating requirements-dev.txt...$(NC)"
	pip freeze > requirements-dev.txt
	@echo "$(GREEN)✅ Dev package $(PACKAGE) installed and requirements-dev.txt updated$(NC)"

# Update requirements.txt with currently installed packages (your existing command)
freeze-req:
	@echo "$(GREEN)Generating requirements.txt from current environment...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✅ requirements.txt updated$(NC)"

# Install all packages from requirements.txt
requirements:
	@if [ -f requirements.txt ]; then \
		echo "$(GREEN)Installing packages from requirements.txt...$(NC)"; \
		pip install -r requirements.txt; \
		echo "$(GREEN)✅ All packages installed$(NC)"; \
	else \
		echo "$(RED)Error: requirements.txt not found$(NC)"; \
		exit 1; \
	fi

# Update all packages and regenerate requirements.txt
update-requirements:
	@echo "$(GREEN)Updating all packages...$(NC)"
	pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
	@echo "$(GREEN)Regenerating requirements.txt...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✅ All packages updated and requirements.txt regenerated$(NC)"

# Uninstall a package and update requirements.txt
uninstall:
ifndef PACKAGE
	@echo "$(RED)Error: PACKAGE variable is required$(NC)"
	@echo "Usage: make uninstall PACKAGE=<package_name>"
	@exit 1
endif
	@echo "$(GREEN)Uninstalling $(PACKAGE)...$(NC)"
	pip uninstall -y $(PACKAGE)
	@echo "$(GREEN)Updating requirements.txt...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✅ Package $(PACKAGE) uninstalled and requirements.txt updated$(NC)"

# === UTILITY COMMANDS ===

# Clean up Python cache files
clean:
	@echo "$(GREEN)Cleaning up cache files...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@if [ -f ".backend.pid" ]; then rm .backend.pid; fi
	@if [ -f "$(REACT_DIR)/.frontend.pid" ]; then rm $(REACT_DIR)/.frontend.pid; fi
	@echo "$(GREEN)✅ Cache files cleaned$(NC)"

# Show current package versions
show-versions:
	@echo "$(GREEN)Current package versions:$(NC)"
	pip list

# Show outdated packages
show-outdated:
	@echo "$(GREEN)Outdated packages:$(NC)"
	pip list --outdated
