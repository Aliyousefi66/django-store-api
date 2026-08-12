from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from products.models import Product
from .cart import RedisCart
from .serializers import CartItemAddSerializer, CartItemResponseSerializer


class CartView(APIView):
    """
    مدیریت عملیات اصلی سبد خرید (نمایش، اضافه کردن و حذف) در ردیس
    """

    def get(self, request):
        """نمایش کل اقلام سبد خرید و قیمت نهایی"""
        cart = RedisCart(request)
        # پاس دادن ژنراتورِ سبد خرید به سریالایزر خروجی
        serializer = CartItemResponseSerializer(cart, many=True)

        return Response({
            'items': serializer.data,
            'total_price': cart.get_total_price(),
            'total_items': len(cart)
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=CartItemAddSerializer)
    def post(self, request):
        """افزودن محصول به سبد خرید یا تغییر تعداد آن"""
        serializer = CartItemAddSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            override_quantity = serializer.validated_data['override_quantity']

            # پیدا کردن محصول از دیتابیس اصلی
            product = get_object_or_404(Product, id=product_id, is_active=True)

            # چک کردن موجودی انبار قبل ار افرودن در سبد خرید
            if product.stock < quantity:
                return Response(
                    {'error': f"موجودی این کالا کافی نیست، حداکثر موجودی: {product.stock}عدد "},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # اضافه کردن به ردیس
            cart = RedisCart(request)
            cart.add(product=product, quantity=quantity, override_quantity=override_quantity)

            return Response({'message': 'آیتم با موفقیت به سبد خرید اضافه شد.'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=CartItemAddSerializer)
    def delete(self, request):
        """حذف یک محصول خاص از سبد خرید"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'ارسال product_id الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        cart = RedisCart(request)
        cart.remove(product)

        return Response({'message': 'محصول از سبد خرید حذف شد.'}, status=status.HTTP_200_OK)
