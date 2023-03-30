from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend import views

router = DefaultRouter()
router.register("products", views.ProductAPIView, basename='products')
router.register("category", views.CategoryAPIView, basename='category')
router.register("shops", views.ShopAPIView, basename='shops')
router.register("product_info", views.ProductInfoAPIView, basename='product_info')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('users/', views.users_view, name='users'),
    path('partner_order/', views.PartnerOrdersAPIView.as_view(), name='partner-load')
]