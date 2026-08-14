from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'price', 'quantity', 'total_price')

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'user', 'address', 'postal_code', 'status',
                  'coupon', 'total_price', 'discount_amount', 'final_price',
                  'items', 'created_at')
        read_only_fields = ('user', 'status', 'coupon', 'total_price', 'discount_amount', 'final_price')

class CreateOrderSerializer(serializers.Serializer):
    address = serializers.CharField(required=True)
    postal_code = serializers.CharField(required=False, allow_blank=True, default='')