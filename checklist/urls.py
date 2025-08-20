"""
URL configuration for checklist app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'catalog', views.ChecklistCatalogViewSet)
router.register(r'evaluations', views.ChecklistEvalViewSet)
router.register(r'templates', views.ChecklistTemplateViewSet)

app_name = 'checklist'

urlpatterns = [
    path('', include(router.urls)),
]