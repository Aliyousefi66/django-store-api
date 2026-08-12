from rest_framework import serializers
from products.serializers import ProductSerializer


class CartItemAddSerializer(serializers.Serializer):
    """
    این سریالایزر ورودی است (وقتی کاربر میحواهد کالایی را اضافه کند)
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    override_quantity = serializers.BooleanField(default=False)

class CartItemResponseSerializer(serializers.Serializer):
    """
    نفش این سریالایزر  خروجی است (برای نمایش سبد خرید به کاربر)
    """
    product = ProductSerializer(read_only=True)
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2)