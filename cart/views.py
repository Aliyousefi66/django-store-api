from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer
from products.models import Product

class CartDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class AddToCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            product = get_object_or_404(Product, id=product_id, is_active=True)
            cart, _ = Cart.objects.get_or_create(user=request.user)

            if product.stock < quantity:
                return Response(
                    {"detail": f"موجودی انبار کافی نیست. موجودی فعلی: {product.stock}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            return Response({"detail": "محصول با موفقیت به سبد خرید اضافه شد."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        caer_item = get_object_or_404(CartItem, cart=cart, id=item_id)
        caer_item.delete()
        return Response({"detail": "آیتم با موفقیت از سبد خرید حدف شد."}, status=status.HTTP_200_OK)

