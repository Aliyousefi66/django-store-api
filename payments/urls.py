from django.urls import path
from .views import ProcessPaymentView

urlpatterns = [
    path('process/<int:order_pk>/', ProcessPaymentView.as_view(), name='payment-process'),
]