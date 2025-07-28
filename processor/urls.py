"""
URL configuration for processor app
"""
from django.urls import path
from . import views

urlpatterns = [
    path('process/', views.DocumentUploadView.as_view(), name='process_document'),
    path('search/', views.DocumentSearchView.as_view(), name='search_documents'),
    path('stats/', views.StatsView.as_view(), name='get_stats'),
]
