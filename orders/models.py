from django.db import models
from django.conf import settings

from coupons.models import Coupon
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('canceled', 'لغو شده'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    coupon = models.ForeignKey('coupons.Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0) # قیمت قبل تخفیف
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0) # میزان تخفیف
    final_price = models.DecimalField(max_digits=12, decimal_places=2, default=0) # قیمت نهایی پرداختی

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"

    @property
    def total_price(self):
        return self.price * self.quantity
