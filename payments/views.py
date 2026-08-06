import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db import transaction

from orders.models import Order
from products.models import Product
from .models import Payment

class ProcessPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, order_pk):
        order = get_object_or_404(Order, pk=order_pk, user=request.user)
        if order.status == 'paid':
            return Response(
                {"detail": "این سفارش قبلا پرداخت شده است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in order.items.all():
            if item.product.stock < item.quantity:
                return Response(
                    {"detail": f"موجودی کالا {item.product.name}کافی نیست."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={'amount': order.total_price}
            )

            fake_ref_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
            payment.status = 'successful'
            payment.ref_id = fake_ref_id
            payment.save()

            order.status = 'paid'
            order.save()

            for item in order.items.all():
                item.product.stock -= item.quantity
                item.product.save()

        return Response({
            "detail": "پرداخت با موفقیت انجام شد.",
            "ref_id": fake_ref_id,
            "order_id": order.pk,
            "total_paid": order.total_price,
        }, status=status.HTTP_200_OK)

