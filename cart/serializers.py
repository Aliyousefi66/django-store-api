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


class CartResponseSerializer(serializers.Serializer):
    """
    سریالایزر اصلی برای رندر کردن کل سبد خرید خروجی
    """
    items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    def _get_cart_items_list(self, obj):
        if not hasattr(self, '_cached_items_list'):
            self._cached_items_list = list(obj)
        return self._cached_items_list

    def get_items(self, obj):
        valid_items = self._get_cart_items_list(obj)
        return CartItemResponseSerializer(valid_items, many=True).data
        # raw_list = list(obj)
        # print('raw_list', raw_list)
        # return raw_list

    def get_total_items(self, obj):
        return len(obj)
        # try:
        #     return len(obj)
        # except:
        #     return 0

    def get_total_price(self, obj):
        valid_items = self._get_cart_items_list(obj)
        return sum(item.get('total_price', 0) for item in valid_items)
        # return 0

    def get_discount_amount(self, obj):
        if hasattr(obj, 'get_discount'):
            return obj.get_discount()
        return 0.0

        # from cart.cart import RedisCart
        # request = self.context.get('request')
        # if request:
        #     return RedisCart(request).get_discount()
        # return 0.0

    def get_final_price(self, obj):
        if hasattr(obj, 'get_total_price'):
            return obj.get_total_price()
        return self.get_discount_amount(obj)

        # from cart.cart import RedisCart
        # request = self.context.get('request')
        # if request:
        #     return RedisCart(request).get_total_price()
        # return self.get_total_price(obj)