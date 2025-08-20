"""
URL configuration for search app.
"""
from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_content, name='search_content'),
    path('suggestions/', views.search_suggestions, name='search_suggestions'),
    path('reindex/', views.reindex_encounter, name='reindex_encounter'),
    path('analytics/', views.search_analytics, name='search_analytics'),
]