from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, request
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema

from products.models import Product
from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer
from cart.cart import RedisCart

class CreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(request_body=CreateOrderSerializer)
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart = RedisCart(request)
        if len(cart) == 0:
            return Response({"detail": "سبد شما خالی است."}, status=status.HTTP_400_BAD_REQUEST)

        for cart_item in cart:
            product = cart_item['product']
            quantity = cart_item['quantity']
            if product.stock < quantity:
                return Response(
                    {"detail": f"متاسفانه موجودی محصول '{product.name}' کافی نیست (موجودی فعلی: {product.stock})."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=serializer.validated_data['address'],
                postal_code=serializer.validated_data['postal_code'],
                coupon=cart.coupon,
                total_price=sum(item['total_price'] for item in cart), # جمع کل خام
                discount_amount=cart.get_discount(), # میزان تخفیف
                final_price=cart.get_total_price(), # مبلغ نهایی
            )

            for cart_item in cart:
                product = cart_item['product']
                quantity = cart_item['quantity']

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=cart_item['price'],
                    quantity=quantity,
                )

                product.stock -= quantity
                product.save()
                
            cart.clear()

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)