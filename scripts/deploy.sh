#!/bin/bash

# SOAPify Deployment Script
set -e

echo "🚀 Starting SOAPify deployment..."

# Configuration
ENVIRONMENT=${1:-production}
DOMAIN=${2:-soapify.local}
BACKUP_BEFORE_DEPLOY=${BACKUP_BEFORE_DEPLOY:-true}

echo "📋 Environment: $ENVIRONMENT"
echo "🌐 Domain: $DOMAIN"

# Check if required files exist
if [ ! -f ".env.${ENVIRONMENT}" ]; then
    echo "❌ Error: .env.${ENVIRONMENT} file not found"
    exit 1
fi

if [ ! -f "docker-compose.${ENVIRONMENT}.yml" ]; then
    echo "❌ Error: docker-compose.${ENVIRONMENT}.yml file not found"
    exit 1
fi

# Create backup if requested
if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
    echo "💾 Creating backup before deployment..."
    ./scripts/backup.sh
fi

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml down

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml pull

# Build application
echo "🔨 Building application..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml build --no-cache web

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml run --rm web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml run --rm web python manage.py collectstatic --noinput

# Start services
echo "▶️ Starting services..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check health
echo "🔍 Checking service health..."
for service in web db redis; do
    if docker-compose -f docker-compose.${ENVIRONMENT}.yml ps $service | grep -q "healthy\|Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not healthy"
        docker-compose -f docker-compose.${ENVIRONMENT}.yml logs $service
        exit 1
    fi
done

# Run post-deployment tasks
echo "🔧 Running post-deployment tasks..."

# Create superuser if it doesn't exist
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@soapify.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
EOF

# Load initial data
echo "📊 Loading initial data..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web python manage.py loaddata fixtures/initial_data.json || echo "No fixtures found, skipping..."

# Create default checklist items
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web python manage.py shell << EOF
from checklist.models import ChecklistCatalog
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

if admin_user and not ChecklistCatalog.objects.exists():
    # Create default checklist items
    checklist_items = [
        {
            'title': 'Chief Complaint',
            'description': 'Patient\'s primary reason for the visit',
            'category': 'subjective',
            'priority': 'critical',
            'keywords': ['complaint', 'problem', 'concern', 'issue'],
            'question_template': 'What is the patient\'s main complaint or concern?'
        },
        {
            'title': 'History of Present Illness',
            'description': 'Detailed history of the current problem',
            'category': 'subjective',
            'priority': 'high',
            'keywords': ['history', 'symptoms', 'duration', 'onset'],
            'question_template': 'Can you describe the history and timeline of the current symptoms?'
        },
        {
            'title': 'Vital Signs',
            'description': 'Basic vital signs measurement',
            'category': 'objective',
            'priority': 'high',
            'keywords': ['blood pressure', 'temperature', 'pulse', 'respiratory rate'],
            'question_template': 'What are the patient\'s current vital signs?'
        },
        {
            'title': 'Physical Examination',
            'description': 'Physical examination findings',
            'category': 'objective',
            'priority': 'high',
            'keywords': ['examination', 'palpation', 'auscultation', 'inspection'],
            'question_template': 'What were the findings from the physical examination?'
        },
        {
            'title': 'Assessment/Diagnosis',
            'description': 'Clinical assessment and diagnosis',
            'category': 'assessment',
            'priority': 'critical',
            'keywords': ['diagnosis', 'assessment', 'impression', 'condition'],
            'question_template': 'What is your clinical assessment and diagnosis?'
        },
        {
            'title': 'Treatment Plan',
            'description': 'Treatment and management plan',
            'category': 'plan',
            'priority': 'critical',
            'keywords': ['treatment', 'medication', 'therapy', 'management'],
            'question_template': 'What is the treatment plan for this patient?'
        }
    ]
    
    for item_data in checklist_items:
        ChecklistCatalog.objects.create(
            created_by=admin_user,
            **item_data
        )
    
    print(f'Created {len(checklist_items)} default checklist items')
else:
    print('Checklist items already exist or no admin user found')
EOF

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Application is available at: https://$DOMAIN"
echo "👤 Admin interface: https://$DOMAIN/admin/"
echo "📊 Admin Plus: https://$DOMAIN/adminplus/"
echo "🌸 Flower monitoring: https://flower.$DOMAIN (if configured)"
echo ""
echo "🔑 Default admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo "   ⚠️  Please change the default password immediately!"
echo ""
echo "📋 Next steps:"
echo "1. Update admin password"
echo "2. Configure environment variables"
echo "3. Set up SSL certificates"
echo "4. Configure monitoring and alerts"
echo "5. Set up regular backups"