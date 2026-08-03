from django.urls import path
from .views import CartDetailView, AddToCartView, RemoveFromCartView

urlpatterns = [
    path('', CartDetailView.as_view(), name='cart-detail'),
    path('add/', AddToCartView.as_view(), name='cart-add'),
    path('remove/<int:item_id>/', RemoveFromCartView.as_view(), name='cart-remove'),
]