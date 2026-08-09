from django.urls import path
from .views import CouponApplyView

app_name = 'coupons'

urlpatterns = [
    path('apply/', CouponApplyView.as_view(), name='apply'),
]