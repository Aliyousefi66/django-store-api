from django.urls import path
from .views import CreateOrderView, OrderListView

urlpatterns = [
    path('create/', CreateOrderView.as_view(), name='order-create'),
    path('history/', OrderListView.as_view(), name='order-history'),
]