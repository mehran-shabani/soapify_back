#!/bin/bash

# SOAPify Full Stack Quick Start Script

echo "🚀 Starting SOAPify Full Stack Application..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. You may want to edit it with your settings."
fi

# Check if front/node_modules exists
if [ ! -d "front/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd front && npm install && cd ..
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.fullstack.yml build

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.fullstack.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.fullstack.yml exec -T web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose -f docker-compose.fullstack.yml exec -T web python manage.py collectstatic --noinput

# Check if superuser exists
echo "👤 Checking for admin user..."
docker-compose -f docker-compose.fullstack.yml exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exists = User.objects.filter(username='admin').exists(); print('EXISTS' if exists else 'NOT_EXISTS')" | grep -q "NOT_EXISTS"

if [ $? -eq 0 ]; then
    echo "Creating default admin user (username: admin, password: admin123)..."
    docker-compose -f docker-compose.fullstack.yml exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"
    echo "⚠️  Please change the admin password after first login!"
fi

# Show status
echo ""
echo "✅ SOAPify Full Stack is running!"
echo ""
echo "🌐 Access URLs:"
echo "   Frontend: http://localhost"
echo "   Backend API: http://localhost:8000/api"
echo "   Admin Panel: http://localhost:8000/admin"
echo "   API Tester: http://localhost/api-tester"
echo ""
echo "📝 Default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📖 For more commands, see FULLSTACK_README.md"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.fullstack.yml down"