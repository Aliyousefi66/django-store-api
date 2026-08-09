from decimal import Decimal

from django.db import models
from django.conf import settings
from products.models import Product

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    coupon = models.ForeignKey('coupons.Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        base_total = sum(item.total_price for item in self.items.all())
        if self.coupon:
            discount_percent = Decimal(self.coupon.discount) / Decimal(100)
            discount_amount = base_total * discount_percent
            return base_total - discount_amount
        return base_total

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.product.price * self.quantity
