#!/bin/bash

echo "🚀 Starting SOAPify Full Stack..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example.full .env
    echo "⚠️  Please edit .env file with your actual configuration!"
fi

# Build and start all services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.full.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.full.yml ps

echo ""
echo "✅ SOAPify Full Stack is starting up!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔗 Backend API: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/swagger/"
echo "👤 Admin Panel: http://localhost:8000/admin/"
echo ""
echo "🔑 Default login credentials:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📋 To stop all services:"
echo "   docker-compose -f docker-compose.full.yml down"
echo ""
echo "📊 To view logs:"
echo "   docker-compose -f docker-compose.full.yml logs -f"
echo ""

# Create superuser if it doesn't exist
echo "👤 Creating default admin user..."
docker-compose -f docker-compose.full.yml exec -T backend python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@soapify.com', 'admin')
    print('✅ Admin user created: admin/admin')
else:
    print('ℹ️  Admin user already exists')
EOF

echo ""
echo "🎉 Setup complete! You can now access the application."