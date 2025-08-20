#!/bin/bash

# SOAPify Health Check Script
set -e

echo "🔍 SOAPify Health Check"
echo "======================="

# Configuration
ENVIRONMENT=${1:-production}
BASE_URL=${BASE_URL:-http://localhost:8000}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $service_name... "
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

# Function to check docker service
check_docker_service() {
    local service_name=$1
    
    echo -n "Checking Docker service $service_name... "
    
    if docker-compose -f docker-compose.${ENVIRONMENT}.yml ps $service_name | grep -q "Up\|healthy"; then
        echo -e "${GREEN}✅ Running${NC}"
        return 0
    else
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
}

# Check Docker services
echo "🐳 Docker Services:"
DOCKER_FAILED=0
for service in web db redis celery-worker celery-beat; do
    check_docker_service $service || DOCKER_FAILED=1
done

echo ""

# Check HTTP endpoints
echo "🌐 HTTP Endpoints:"
HTTP_FAILED=0
check_service "Main Application" "$BASE_URL/admin/health/" 200 || HTTP_FAILED=1
check_service "Admin Interface" "$BASE_URL/admin/" 302 || HTTP_FAILED=1
check_service "API Health" "$BASE_URL/api/health/" 200 || HTTP_FAILED=1

echo ""

# Check database connectivity
echo "🗄️ Database:"
echo -n "Checking database connectivity... "
if docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web python manage.py check --database default >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Connected${NC}"
    DB_FAILED=0
else
    echo -e "${RED}❌ Connection failed${NC}"
    DB_FAILED=1
fi

# Check Redis connectivity
echo -n "Checking Redis connectivity... "
if docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✅ Connected${NC}"
    REDIS_FAILED=0
else
    echo -e "${RED}❌ Connection failed${NC}"
    REDIS_FAILED=1
fi

echo ""

# Check Celery workers
echo "⚙️ Celery Workers:"
echo -n "Checking active workers... "
ACTIVE_WORKERS=$(docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web celery -A soapify inspect active 2>/dev/null | grep -c "celery@" || echo "0")
if [ "$ACTIVE_WORKERS" -gt 0 ]; then
    echo -e "${GREEN}✅ $ACTIVE_WORKERS workers active${NC}"
    CELERY_FAILED=0
else
    echo -e "${RED}❌ No active workers${NC}"
    CELERY_FAILED=1
fi

echo ""

# Check disk space
echo "💾 System Resources:"
echo -n "Checking disk space... "
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✅ ${DISK_USAGE}% used${NC}"
    DISK_FAILED=0
else
    echo -e "${YELLOW}⚠️ ${DISK_USAGE}% used (high usage)${NC}"
    DISK_FAILED=1
fi

# Check memory usage
echo -n "Checking memory usage... "
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✅ ${MEMORY_USAGE}% used${NC}"
    MEMORY_FAILED=0
else
    echo -e "${YELLOW}⚠️ ${MEMORY_USAGE}% used (high usage)${NC}"
    MEMORY_FAILED=1
fi

echo ""

# Summary
echo "📊 Health Check Summary:"
echo "========================"

TOTAL_FAILED=$((DOCKER_FAILED + HTTP_FAILED + DB_FAILED + REDIS_FAILED + CELERY_FAILED + DISK_FAILED + MEMORY_FAILED))

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All systems operational${NC}"
    exit 0
else
    echo -e "${RED}❌ $TOTAL_FAILED issue(s) detected${NC}"
    
    # Show detailed logs for failed services
    echo ""
    echo "🔍 Troubleshooting Information:"
    
    if [ $DOCKER_FAILED -eq 1 ]; then
        echo "Docker service logs:"
        docker-compose -f docker-compose.${ENVIRONMENT}.yml logs --tail=20
    fi
    
    if [ $HTTP_FAILED -eq 1 ]; then
        echo "Web service logs:"
        docker-compose -f docker-compose.${ENVIRONMENT}.yml logs web --tail=20
    fi
    
    exit 1
fi