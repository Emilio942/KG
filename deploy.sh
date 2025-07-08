#!/bin/bash

# KG-System Production Deployment Script
# This script automates the deployment of the KG-System to production

set -e  # Exit on any error

# Configuration
DEPLOYMENT_TYPE=${1:-"docker"}  # docker, kubernetes, or local
ENVIRONMENT=${2:-"production"}
VERSION=${3:-"latest"}
REGISTRY=${4:-"local"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Kubernetes (if needed)
    if [ "$DEPLOYMENT_TYPE" == "kubernetes" ]; then
        if ! command -v kubectl &> /dev/null; then
            log_error "kubectl is not installed"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    log_info "Building KG-System Docker image..."
    
    docker build -t kg-system:$VERSION .
    
    if [ "$REGISTRY" != "local" ]; then
        log_info "Tagging image for registry: $REGISTRY"
        docker tag kg-system:$VERSION $REGISTRY/kg-system:$VERSION
        docker tag kg-system:$VERSION $REGISTRY/kg-system:latest
    fi
    
    log_success "Docker image built successfully"
}

# Push to registry
push_image() {
    if [ "$REGISTRY" != "local" ]; then
        log_info "Pushing image to registry: $REGISTRY"
        docker push $REGISTRY/kg-system:$VERSION
        docker push $REGISTRY/kg-system:latest
        log_success "Image pushed to registry"
    fi
}

# Deploy with Docker Compose
deploy_docker() {
    log_info "Deploying KG-System with Docker Compose..."
    
    # Create necessary directories
    mkdir -p logs models data/postgres data/redis
    
    # Set environment variables
    export ENVIRONMENT=$ENVIRONMENT
    export VERSION=$VERSION
    export REGISTRY=$REGISTRY
    
    # Generate secrets if they don't exist
    if [ ! -f .env ]; then
        log_info "Creating environment file..."
        cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)
ENVIRONMENT=$ENVIRONMENT
VERSION=$VERSION
EOF
    fi
    
    # Start services
    docker-compose down --remove-orphans
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Run database migrations
    docker-compose exec kg-api python -m alembic upgrade head
    
    log_success "Docker deployment completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying KG-System to Kubernetes..."
    
    # Create namespace
    kubectl create namespace kg-system --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets
    kubectl create secret generic kg-secrets \
        --from-literal=postgres-password="$(openssl rand -base64 32)" \
        --from-literal=redis-password="$(openssl rand -base64 32)" \
        --from-literal=jwt-secret="$(openssl rand -base64 64)" \
        --namespace=kg-system \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s-deployment.yaml
    
    # Wait for deployment to be ready
    kubectl rollout status deployment/kg-api -n kg-system
    
    log_success "Kubernetes deployment completed"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    local endpoint=""
    
    if [ "$DEPLOYMENT_TYPE" == "docker" ]; then
        endpoint="http://localhost:8000"
    elif [ "$DEPLOYMENT_TYPE" == "kubernetes" ]; then
        endpoint="http://$(kubectl get svc kg-api-service -n kg-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8000"
    fi
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f "$endpoint/health" > /dev/null 2>&1; then
            log_success "Health check passed"
            break
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "Health checks failed after $max_attempts attempts"
        exit 1
    fi
    
    # Test key endpoints
    log_info "Testing key endpoints..."
    
    # Test status endpoint
    if curl -f "$endpoint/status" > /dev/null 2>&1; then
        log_success "Status endpoint: OK"
    else
        log_warning "Status endpoint: FAILED"
    fi
    
    # Test metrics endpoint
    if curl -f "$endpoint/metrics" > /dev/null 2>&1; then
        log_success "Metrics endpoint: OK"
    else
        log_warning "Metrics endpoint: FAILED"
    fi
}

# Run performance tests
run_performance_tests() {
    log_info "Running performance tests..."
    
    # Install dependencies for testing
    pip install locust
    
    # Create simple load test
    cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class KGSystemUser(HttpUser):
    wait_time = between(1, 5)
    
    @task
    def test_status(self):
        self.client.get("/status")
    
    @task
    def test_health(self):
        self.client.get("/health")
    
    @task
    def test_metrics(self):
        self.client.get("/metrics")
EOF
    
    # Run load test
    locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host=http://localhost:8000
    
    # Cleanup
    rm locustfile.py
    
    log_success "Performance tests completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    if [ "$DEPLOYMENT_TYPE" == "docker" ]; then
        # Prometheus and Grafana are already included in docker-compose
        log_info "Monitoring services are included in Docker Compose"
        
        # Wait for Grafana to be ready
        sleep 30
        
        # Import Grafana dashboards
        curl -X POST \
            -H "Content-Type: application/json" \
            -d '{"dashboard": {"id": null, "title": "KG-System Overview", "panels": []}, "overwrite": true}' \
            http://admin:admin@localhost:3000/api/dashboards/db
    fi
    
    log_success "Monitoring setup completed"
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report..."
    
    local report_file="deployment_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > $report_file << EOF
KG-System Deployment Report
==========================

Deployment Details:
- Type: $DEPLOYMENT_TYPE
- Environment: $ENVIRONMENT
- Version: $VERSION
- Registry: $REGISTRY
- Timestamp: $(date)

Services Status:
EOF
    
    if [ "$DEPLOYMENT_TYPE" == "docker" ]; then
        echo "Docker Compose Services:" >> $report_file
        docker-compose ps >> $report_file
    elif [ "$DEPLOYMENT_TYPE" == "kubernetes" ]; then
        echo "Kubernetes Resources:" >> $report_file
        kubectl get all -n kg-system >> $report_file
    fi
    
    echo "" >> $report_file
    echo "Endpoints:" >> $report_file
    
    if [ "$DEPLOYMENT_TYPE" == "docker" ]; then
        echo "- API: http://localhost:8000" >> $report_file
        echo "- Metrics: http://localhost:8000/metrics" >> $report_file
        echo "- Dashboard: http://localhost:3000" >> $report_file
    fi
    
    log_success "Deployment report generated: $report_file"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f locustfile.py
}

# Main deployment function
main() {
    log_info "Starting KG-System deployment..."
    log_info "Deployment type: $DEPLOYMENT_TYPE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    build_image
    push_image
    
    case $DEPLOYMENT_TYPE in
        "docker")
            deploy_docker
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
        "local")
            log_info "Local deployment - skipping container deployment"
            ;;
        *)
            log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Post-deployment steps
    sleep 30  # Allow services to stabilize
    run_health_checks
    setup_monitoring
    
    # Optional performance tests
    if [ "$ENVIRONMENT" == "production" ]; then
        read -p "Run performance tests? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_performance_tests
        fi
    fi
    
    generate_report
    
    log_success "KG-System deployment completed successfully!"
    log_info "Access the system at: http://localhost:8000"
    log_info "Monitor at: http://localhost:3000 (Grafana)"
    log_info "Metrics at: http://localhost:9090 (Prometheus)"
}

# Help function
show_help() {
    cat << EOF
KG-System Deployment Script

Usage: $0 [DEPLOYMENT_TYPE] [ENVIRONMENT] [VERSION] [REGISTRY]

Parameters:
  DEPLOYMENT_TYPE  Type of deployment (docker, kubernetes, local) [default: docker]
  ENVIRONMENT      Environment name (development, staging, production) [default: production]
  VERSION          Version tag for the image [default: latest]
  REGISTRY         Container registry URL [default: local]

Examples:
  $0                                    # Deploy with Docker Compose locally
  $0 docker production v1.0.0          # Deploy specific version
  $0 kubernetes production latest       # Deploy to Kubernetes
  $0 docker development                 # Deploy development environment

Options:
  -h, --help       Show this help message

EOF
}

# Parse command line arguments
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"
