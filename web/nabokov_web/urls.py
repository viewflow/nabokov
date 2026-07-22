from django.urls import path

from . import views

urlpatterns = [
    path("api/lint", views.lint),
    path("api/health", views.health),
]
