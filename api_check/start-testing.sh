#!/bin/bash

echo "🚀 Starting Soapify API Testing System"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# check_service reports whether the previously run command succeeded for the given service name and exits with status 1 on failure.
check_service() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1 started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start $1${NC}"
        exit 1
    fi
}

# Check if running on server or local
echo -e "${BLUE}Where are you running this script?${NC}"
echo "1) On the server (for monitoring)"
echo "2) On local machine (for testing)"
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo -e "${YELLOW}Starting Server Monitoring...${NC}"
        cd server_check_server
        
        # Check if .env exists
        if [ ! -f .env ]; then
            echo -e "${YELLOW}Creating .env file...${NC}"
            cp .env.example .env 2>/dev/null || echo "No .env.example found"
            echo -e "${YELLOW}Please edit .env file with your settings${NC}"
            read -p "Press enter when ready..."
        fi
        
        # Start services
        docker-compose up -d
        check_service "Server Monitoring"
        
        echo -e "${GREEN}Server monitoring is running!${NC}"
        echo -e "Dashboard: ${BLUE}http://localhost:8080${NC}"
        echo -e "Prometheus: ${BLUE}http://localhost:9090${NC}"
        echo -e "Grafana: ${BLUE}http://localhost:3000${NC}"
        ;;
        
    2)
        echo -e "${YELLOW}Starting Frontend Testing...${NC}"
        cd front_check_server
        
        # Check if .env exists
        if [ ! -f .env ]; then
            echo -e "${YELLOW}Creating .env file...${NC}"
            cp .env.example .env
            echo -e "${RED}IMPORTANT: Edit .env file and set SERVER_MONITOR_URL to your server address${NC}"
            read -p "Press enter when ready..."
        fi
        
        # Start services
        docker-compose up -d
        check_service "Frontend Testing"
        
        echo -e "${GREEN}Frontend testing app is running!${NC}"
        echo -e "React App: ${BLUE}http://localhost:3000${NC}"
        echo -e "File Server: ${BLUE}http://localhost:8081${NC}"
        
        # Check server connection
        echo -e "\n${YELLOW}Checking connection to monitoring server...${NC}"
        SERVER_URL=$(grep SERVER_MONITOR_URL .env | cut -d '=' -f2)
        if curl -s "$SERVER_URL/api/metrics/system" > /dev/null; then
            echo -e "${GREEN}✓ Connected to monitoring server${NC}"
        else
            echo -e "${RED}✗ Cannot connect to monitoring server at $SERVER_URL${NC}"
            echo -e "${YELLOW}Make sure the server monitoring is running and accessible${NC}"
        fi
        ;;
        
    *)
        echo -e "${RED}Invalid choice. Please run the script again.${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}To view logs: docker-compose logs -f${NC}"
echo -e "${YELLOW}To stop: docker-compose down${NC}"