from django.urls import path

from . import views

urlpatterns = [
    path("api/lint", views.lint),
    path("api/profiles", views.profiles),
    path("api/health", views.health),
]
