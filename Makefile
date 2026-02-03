.PHONY: help bootstrap docker-build docker-run docker-stop test lint clean deploy

# Default target
help:
	@echo "Service Order Specialist Agent - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  bootstrap     Install dependencies and setup environment"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  clean        Clean up temporary files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run agent in Docker container"  
	@echo "  docker-stop  Stop Docker container"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy       Deploy to production"

bootstrap:
	@echo "Setting up Service Order Specialist Agent..."
	pip install -r requirements.txt
	cp .env.example .env
	@echo "✅ Bootstrap complete! Edit .env with your configuration."

docker-build:
	@echo "Building Service Order Specialist Agent Docker image..."
	docker build -t service-order-specialist:latest .
	@echo "✅ Docker image built successfully"

docker-run:
	@echo "Starting Service Order Specialist Agent..."
	docker run --name service-order-specialist \
		--env-file .env \
		-p 8000:8000 \
		-d service-order-specialist:latest
	@echo "✅ Agent started at http://localhost:8000"
	@echo "📊 Agent Card: http://localhost:8000/.well-known/agent-card.json"

docker-stop:
	@echo "Stopping Service Order Specialist Agent..."
	docker stop service-order-specialist || true
	docker rm service-order-specialist || true
	@echo "✅ Agent stopped"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "✅ Tests complete"

lint:
	@echo "Running lint checks..."
	flake8 agent.py
	black --check agent.py
	@echo "✅ Lint checks passed"

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.pyc
	@echo "✅ Cleanup complete"

deploy:
	@echo "🚀 Deploying Service Order Specialist Agent..."
	@echo "This would typically involve:"
	@echo "  1. Building and pushing Docker image to registry"
	@echo "  2. Updating Kubernetes deployment"  
	@echo "  3. Registering with A2A discovery service"
	@echo "  4. Configuring Slack app integration"
	@echo ""
	@echo "Manual steps needed for full deployment:"
	@echo "  - Configure Kubernetes deployment YAML"
	@echo "  - Set up Slack app with proper permissions" 
	@echo "  - Register agent endpoints with A2A discovery"
	@echo "  - Configure monitoring and alerting"