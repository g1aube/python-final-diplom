from django.contrib.auth import authenticate, login
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
import yaml
from backend.forms import UserRegistrationForm, LoginForm
from backend.models import User, Product, ProductInfo, Category, Shop, Order, OrderItem, Parameter, ProductParameter
from .serializers import ProductSerializer, ProductInfoSerializer, CategorySerializer, ShopSerializer, OrderSerializer


def register_view(request):
    "--> Регистрация пользователей"
    base_template_register = 'register.html'
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            template_name = 'registration_completed.html'
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            return render(request, template_name, {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request, base_template_register, {'user_form': user_form})

def login_view(request):
    "--> Авторизация пользователей"
    base_template_login = 'login.html'
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(username=cd['username'],
                                password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Аутентификация прошла успешно')
                else:
                    return HttpResponse('Аккаунт заблокирован, пожалуйста, обратитесь к администратору сайта')
            else:
                return HttpResponse('Неверный логин или пароль')
    else:
        form = LoginForm()
    return render(request, base_template_login, {'form': form})

def users_view(request):
    "Страница всех пользователей сайта"
    base_template_users = 'users.html'
    context = {}
    user = User.objects.all()
    context['user'] = user
    return render(request, base_template_users, context)