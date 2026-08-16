# import uuid
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, permissions
# from django.shortcuts import get_object_or_404
# from django.db import transaction
#
# from orders.models import Order
# from products.models import Product
# from .models import Payment
#
# class ProcessPaymentView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#     def post(self, request, order_pk):
#         order = get_object_or_404(Order, pk=order_pk, user=request.user)
#         if order.status == 'paid':
#             return Response(
#                 {"detail": "این سفارش قبلا پرداخت شده است."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         if order.status == 'canceled':
#             return Response(
#                 {"detail": "این سفارش لغو شده است و امکان پرداخت آن وجود ندارد."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         with transaction.atomic():
#             payment, created = Payment.objects.get_or_create(
#                 order=order,
#                 defaults={'amount': order.final_price}
#             )
#
#             fake_ref_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
#             payment.status = 'successful'
#             payment.ref_id = fake_ref_id
#             payment.save()
#
#             order.status = 'paid'
#             order.save()
#
#         return Response({
#             "detail": "پرداخت با موفقیت انجام شد.",
#             "ref_id": fake_ref_id,
#             "order_id": order.pk,
#             "total_paid": order.final_price,
#             "payment_status": payment.status,
#         }, status=status.HTTP_200_OK)
#

import requests
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from orders.models import Order
from .models import Payment


class PaymentRequestView(APIView):
    """
    ۱. ثبت درخواست پرداخت و هدایت کاربر به درگاه زرین‌پال
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_pk):
        order = get_object_or_404(Order, pk=order_pk, user=request.user)

        # ۱. اعتبارسنجی وضعیت سفارش
        if order.status == 'paid':
            return Response({"detail": "این سفارش قبلاً پرداخت شده است."}, status=status.HTTP_400_BAD_REQUEST)
        if order.status == 'canceled':
            return Response({"detail": "این سفارش لغو شده است."}, status=status.HTTP_400_BAD_REQUEST)

        # ۲. تبدیل مبلغ به تومان (زرین‌پال v4 مبلغ را به تومان می‌گیرد)
        # اگر دیتای شما به ریال است، تقسیم بر ۱۰ کنید.
        amount = int(order.final_price)

        # ۳. ساخت بدنه درخواست برای API زرین‌پال
        data = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount,
            "currency": "IRT", # تومان
            "description": f"پرداخت سفارش شماره #{order.id}",
            "callback_url": settings.ZARINPAL_CALLBACK_URL,
            "metadata": {
                "mobile": str(request.user.phone_number) if hasattr(request.user, 'phone_number') else "",
                "email": request.user.email or ""
            }
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            response = requests.post(settings.ZARINPAL_REQUEST_URL, json=data, headers=headers, timeout=10)
            res_data = response.json()

            # ۴. اگر درخواست درگاه موفق بود
            if response.status_code == 200 and res_data.get('data') and res_data['data'].get('code') == 100:
                authority = res_data['data']['authority']

                # ثبت یا به‌روزرسانی تراکنش پرداخت در دیتابیس خودمان
                Payment.objects.update_or_create(
                    order=order,
                    defaults={
                        'amount': order.final_price,
                        'status': 'pending',
                        'ref_id': authority # موقتا authority را در ref_id می‌گذاریم تا زمان verify
                    }
                )

                gateway_url = f"{settings.ZARINPAL_STARTPAY_URL}{authority}"
                return Response({
                    "detail": "درخواست پرداخت با موفقیت ثبت شد.",
                    "gateway_url": gateway_url,
                    "authority": authority
                }, status=status.HTTP_200_OK)

            return Response({
                "detail": "خطا در ارتباط با درگاه پرداخت.",
                "errors": res_data.get('errors')
            }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({"detail": f"خطای شبکه در ارتباط با درگاه: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class PaymentVerifyView(APIView):
    """
    ۲. تایید نهایی پرداخت پس از بازگشت کاربر از درگاه زرین‌پال
    """
    permission_classes = [permissions.AllowAny] # چون زرین‌پال کاربر را بدون کوکی/توکن ری‌دایرکت می‌کند

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="کد Authority زرین‌پال", type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت پرداخت (OK یا NOK)", type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):
        authority = request.GET.get('Authority')
        payment_status = request.GET.get('Status')

        if not authority or not payment_status:
            return Response({"detail": "اطلاعات بازگشتی از درگاه ناقص است."}, status=status.HTTP_400_BAD_REQUEST)

        # پیدا کردن پرداخت بر اساس Authority ثبت‌شده
        payment = get_object_or_404(Payment, ref_id=authority)
        order = payment.order

        # اگر کاربر در درگاه دکمه انصراف را زده باشد
        if payment_status != 'OK':
            payment.status = 'failed'
            payment.save()
            return Response({"detail": "پرداخت توسط کاربر لغو شد یا با خطا مواجه گردید."}, status=status.HTTP_400_BAD_REQUEST)

        # اگر پرداخت قبلا تایید شده
        if payment.status == 'successful':
            return Response({"detail": "این پرداخت قبلاً تایید شده است.", "ref_id": payment.ref_id}, status=status.HTTP_200_OK)

        # استعلام صحت تراکنش از سرور زرین‌پال (Verify)
        data = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": int(payment.amount),
            "authority": authority
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            response = requests.post(settings.ZARINPAL_VERIFY_URL, json=data, headers=headers, timeout=10)
            res_data = response.json()

            # کد 100 یعنی پرداخت موفق بوده، کد 101 یعنی قبلا تایید شده
            if response.status_code == 200 and res_data.get('data') and res_data['data'].get('code') in [100, 101]:
                ref_id = str(res_data['data']['ref_id'])

                # تراکنش دیتابیس جهت تغییر وضعیت‌ها
                with transaction.atomic():
                    payment.status = 'successful'
                    payment.ref_id = ref_id # ثبت شماره پیگیری واقعی بانک
                    payment.save()

                    order.status = 'paid'
                    order.save()

                return Response({
                    "detail": "پرداخت با موفقیت انجام و تایید شد.",
                    "ref_id": ref_id,
                    "order_id": order.id
                }, status=status.HTTP_200_OK)

            else:
                payment.status = 'failed'
                payment.save()
                return Response({
                    "detail": "تراکنش توسط درگاه تایید نشد.",
                    "errors": res_data.get('errors')
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({"detail": f"خطا در استعلام از درگاه: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
