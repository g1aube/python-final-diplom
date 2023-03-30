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
from .serializers import ProductSerializer, ProductInfoSerializer, CategorySerializer, ShopSerializer, OrderSerializer, OrderItemSerializer


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

class ProductAPIView(ModelViewSet):
    "Список товаров"
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    ordering = ['id']
    search_fields = ['name']

class CategoryAPIView(ModelViewSet):
    "Список категорий"
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['name']

class ShopAPIView(ModelViewSet):
    "Список магазинов"
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    ordering = ['name']
    search_fields = ['name']

class PartnerOrdersAPIView(APIView):
    "Отображение заказов для поставщика"
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Only for registered users'},
                                  status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Only shops'}, status=403)

        order = Order.objects.filter(ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related('ordered_items__product_info__product__category')
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

class ProductInfoAPIView(viewsets.ReadOnlyModelViewSet):
    "Отображение информации о товаре"
    throttle_scope = 'anon'
    serializer_class = ProductInfoSerializer
    ordering = ('product')

    def get_queryset(self):

        query = Q(shop__state=True)
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = ProductInfo.objects.filter(query).select_related(
            'shop', 'product__category'
        ).prefetch_related(
            'product_parameters__parameter'
        ).distinct()

        return queryset


class BasketAPIView(APIView):
    "Работа с корзиной для покупателя"
    # отобразить корзину / get method
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Only for registered users'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category')

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # добавить позицию в корзину / post method
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Only for registered users'}, status=403)

        items = request.data.get('ordered_items')

        if items:
            basket, created = Order.objects.get_or_create(user_id=request.user.id, state='basket')

            objects_created = 0
            for item in items:

                exists_item = OrderItem.objects.filter(order=basket.id, product_info=item["product_info"])
                if len(exists_item) > 0:
                    return JsonResponse({'Status': False, 'Errors': f'Позиция product_info={item["product_info"]}'
                                                                    f' уже есть в корзине'})

                item.update({'order': basket.id})
                serializer = OrderItemSerializer(data=item)
                if serializer.is_valid():
                    serializer.save()
                    objects_created += 1
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})

            return JsonResponse({'Status': True, 'Создано позиций': objects_created})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить позиции из корзины / delete method
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Только для зарегистрированных пользователей'}, status=403)

        items = request.data.get('ordered_items')

        if items:
            basket, created = Order.objects.get_or_create(user_id=request.user.id, state='basket')

            query = Q()
            for item in items:
                query = query | Q(order_id=basket.id, product_info=item["product_info"])

            deleted_count = OrderItem.objects.filter(query).delete()[0]

            return JsonResponse({'Status': True, 'Удалено позиций': deleted_count})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать позиции в корзине / put method
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Только для зарегистрированных пользователей'}, status=403)

        items = request.data.get('ordered_items')

        if items:
            basket, created = Order.objects.get_or_create(user_id=request.user.id, state='basket')

            objects_updated = 0
            for item in items:
                objects_updated += OrderItem.objects.filter(order_id=basket.id, product_info=item['product_info']).\
                    update(quantity=item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class OrderAPIView(APIView):
    "Заказы покупателя"
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Только для зарегистрированных пользователей'}, status=403)

        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').distinct()

        serializer = OrderSerializer(order, many=True)

        return Response(serializer.data)

    # сделать новый заказ из корзины
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Только для зарегистрированных пользователей'}, status=403)

        id_order = request.data['id']

        if id_order:

            data = Order.objects.filter(id=id_order, user=request.user.id, state='basket')

            if len(data) == 0:
                return JsonResponse({'Status': False, 'Errors': 'Не найдена корзина пользователя'})

            data.update(state='new')

            return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class PartnerUpdateAPIView(APIView):
    "Класс для обновления прайса от поставщика"

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Only shop'}, status=403)

        file = request.data.get('url')

        if file:
            data = yaml.load(file, Loader=yaml.FullLoader)

            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)

            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()

            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)

            return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
