"""
URL configuration for document_processor project.
"""
from django.contrib import admin
from django.urls import path, include
from processor.views import home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('processor.urls')),
]
