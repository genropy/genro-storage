.PHONY: help test test-unit test-integration test-all services-start services-stop services-status clean

help:
	@echo "Genro Storage - Test Commands"
	@echo "=============================="
	@echo ""
	@echo "Test commands:"
	@echo "  make test              - Run all tests with services auto-start"
	@echo "  make test-unit         - Run only unit tests (no Docker needed)"
	@echo "  make test-integration  - Run only integration tests (requires Docker)"
	@echo "  make test-all          - Run all tests with coverage report"
	@echo ""
	@echo "Service management:"
	@echo "  make services-start    - Start all test services (Docker)"
	@echo "  make services-stop     - Stop all test services"
	@echo "  make services-status   - Show services status"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Stop services and clean up"

# Start Docker services for integration tests
services-start:
	@echo "Starting test services..."
	@bash scripts/start_test_services.sh

# Stop Docker services
services-stop:
	@echo "Stopping test services..."
	@bash scripts/stop_test_services.sh

# Show services status
services-status:
	@docker-compose ps

# Run all tests (auto-starts services if needed)
test: services-start
	@echo "Running all tests..."
	@pytest tests/ -v

# Run only unit tests (no Docker required)
test-unit:
	@echo "Running unit tests only..."
	@pytest tests/ -v -m "not integration"

# Run only integration tests (requires Docker)
test-integration: services-start
	@echo "Running integration tests..."
	@pytest tests/ -v -m integration

# Run all tests with coverage
test-all: services-start
	@echo "Running all tests with coverage..."
	@pytest tests/ -v --cov=genro_storage --cov-report=html --cov-report=term

# Clean up everything
clean: services-stop
	@echo "Cleaning up..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"
