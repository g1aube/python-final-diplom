from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('users/', views.users_view, name='users')
]