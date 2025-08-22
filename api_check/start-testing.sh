#!/bin/bash

# Soapify API Tester - Unified Application Startup Script

set -e

echo "🚀 Soapify API Tester - Unified Application"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ and npm."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16+ is required. Current version: $(node -v)"
    echo "   Please update Node.js from: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo "✅ npm $(npm -v) detected"
echo ""

# Navigate to the React app directory
cd soapify-api-tester

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install --legacy-peer-deps
    echo "✅ Dependencies installed successfully"
    echo ""
else
    echo "✅ Dependencies already installed"
    echo ""
fi

# Check if API endpoints file exists
if [ ! -f "../api_endpoints_checklist.json" ]; then
    echo "❌ API endpoints file not found: ../api_endpoints_checklist.json"
    echo "   This file contains the complete API endpoint catalog."
    exit 1
fi

echo "✅ API endpoints catalog found ($(jq '.api_endpoints | length' ../api_endpoints_checklist.json) categories)"
echo ""

# Display startup options
echo "🎯 Startup Options:"
echo "1. Start Development Server (Hot Reload)"
echo "2. Build and Serve Production Version"
echo "3. Run Tests"
echo "4. Exit"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting development server..."
        echo "   - Application will be available at: http://localhost:3000"
        echo "   - Grant microphone permissions when prompted"
        echo "   - Press Ctrl+C to stop the server"
        echo ""
        echo "📊 Features Available:"
        echo "   ✅ Real-time API testing"
        echo "   ✅ Audio recording during tests"
        echo "   ✅ Performance analytics"
        echo "   ✅ Resume interrupted sessions"
        echo "   ✅ Export results (JSON/CSV)"
        echo ""
        npm start
        ;;
    2)
        echo ""
        echo "🔨 Building production version..."
        npm run build
        echo "✅ Build completed successfully"
        echo ""
        echo "🚀 Starting production server..."
        echo "   - Application will be available at: http://localhost:3000"
        echo "   - Press Ctrl+C to stop the server"
        echo ""
        npm run serve
        ;;
    3)
        echo ""
        echo "🧪 Running tests..."
        npm test
        ;;
    4)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid option. Please run the script again and select 1-4."
        exit 1
        ;;
esac