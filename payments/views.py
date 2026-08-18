import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from orders.models import Order
from .models import Payment
from .throttling import PaymentRateThrottle

class PaymentRequestView(APIView):
    """
    ۱. ثبت درخواست پرداخت و هدایت کاربر به درگاه زرین‌پال
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentRateThrottle] # محدود کردن نرخ درخواست های این ویو

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
                "email": str(request.user.email) or ""
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
    permission_classes = [
        permissions.AllowAny]  # تنظیم دسترسی آزاد، چون زرین‌پال کاربر را بدون توکن/کوکی به این آدرس هدایت می‌کند

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="کد Authority زرین‌پال",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت پرداخت (OK یا NOK)",
                              type=openapi.TYPE_STRING)
        ]
    )  # مستندسازی پارامترهای ورودی Query String در Swagger
    def get(self, request):
        authority = request.GET.get('Authority')  # دریافت کد پیگیری موقت (Authority) از آدرس URL
        payment_status = request.GET.get('Status')  # دریافت وضعیت پرداخت (OK یا NOK) از آدرس URL

        if not authority or not payment_status:  # اعتبارسنجی حضور هر دو پارامتر ضروری در درخواست
            return Response({"detail": "اطلاعات بازگشتی از درگاه ناقص است."},
                            status=status.HTTP_400_BAD_REQUEST)  # بازگرداندن خطای ۴۰۰ در صورت عدم وجود پارامترها

        # پیدا کردن پرداخت بر اساس Authority ثبت‌شده
        payment = get_object_or_404(Payment,
                                    ref_id=authority)  # جستجوی رکورد پرداخت در دیتابیس با کد Authority یا ارسال خطای ۴۰۴
        order = payment.order  # استخراج سفارش مرتبط با این پرداخت

        # اگر کاربر در درگاه دکمه انصراف را زده باشد
        if payment_status != 'OK':  # بررسی اینکه آیا وضعیت پرداخت از سمت درگاه موفقیت‌آمیز نبوده است
            payment.status = 'failed'  # تغییر وضعیت تراکنش به ناموفق در دیتابیس
            payment.save()  # ذخیره تغییر وضعیت تراکنش
            return Response({"detail": "پرداخت توسط کاربر لغو شد یا با خطا مواجه گردید."},
                            status=status.HTTP_400_BAD_REQUEST)  # بازگرداندن پاسخ لغو پرداخت

        # اگر پرداخت قبلا تایید شده
        if payment.status == 'successful':  # بررسی جهت جلوگیری از تایید مجدد تراکنشی که قبلاً ثبت شده است
            return Response({"detail": "این پرداخت قبلاً تایید شده است.", "ref_id": payment.ref_id},
                            status=status.HTTP_200_OK)  # اعلام قبلی بودن تایید تراکنش

        # استعلام صحت تراکنش از سرور زرین‌پال (Verify)
        data = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,  # کد پذیرنده زرین‌پال از تنظیمات پروژه
            "amount": int(payment.amount),  # مبلغ دقیق پرداخت‌شده (تبدیل شده به عدد صحیح)
            "authority": authority  # کد Authority پرداختی که باید استعلام شود
        }  # ساخت بدنه JSON برای ارسال به API استعلام زرین‌پال

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }  # تنظیم الهامات درخواست (Headers) شامل نوع داده JSON

        try:
            response = requests.post(settings.ZARINPAL_VERIFY_URL, json=data, headers=headers,
                                     timeout=10)  # ارسال درخواست POST به زرین‌پال با تایم‌اوت ۱۰ ثانیه
            res_data = response.json()  # تبدیل پاسخ دریافتی از زرین‌پال به دیکشنری پایتون

            # کد 100 یعنی پرداخت موفق بوده، کد 101 یعنی قبلا تایید شده
            if response.status_code == 200 and res_data.get('data') and res_data['data'].get('code') in [100,
                                                                                                         101]:  # بررسی موفق بودن پاسخ دریافتی از درگاه
                ref_id = str(res_data['data']['ref_id'])  # استخراج شماره پیگیری مرجع (Ref ID) بانک و تبدیل آن به رشته

                # تراکنش دیتابیس جهت تغییر وضعیت‌ها
                with transaction.atomic():  # شروع تراکنش آتومیک برای ضمانت انجام یکپارچه تمام تغییرات دیتابیس یا لغو کامل آن‌ها
                    for item in order.items.select_related(
                            'product').all():  # پیمایش تک‌تک آیتم‌های سفارش با بهینه‌سازی کوئری دیتابیس
                        product = item.product  # استخراج آبجکت محصول مربوط به این آیتم

                        if product.stock < item.quantity:  # اعتبارسنجی موجودی انبار در لحظه ثبت نهایی خرید
                            raise ValueError(
                                f"موجودی محصول '{product.name}' کافی نیست.")  # ایجاد خطای اختصاصی در صورت عدم کفایت موجودی

                        product.stock = F(
                            'stock') - item.quantity  # کسر تعداد خریداری‌شده از موجودی انبار در سطح دیتابیس (جلوگیری از Race Condition)
                        if hasattr(product, 'total_sales'):  # بررسی وجود فیلد تعداد کل فروش روی مدل محصول
                            product.total_sales = F(
                                'total_sales') + item.quantity  # افزایش تعداد کل فروش محصول در سطح دیتابیس
                        product.save()  # ذخیره تغییرات انجام‌شده روی محصول

                    payment.status = 'successful'  # تغییر وضعیت تراکنش پرداخت به موفق
                    payment.ref_id = ref_id  # ثبت شماره پیگیری واقعی بانک به جای Authority موقت
                    payment.save()  # ذخیره تغییرات وضعیت پرداخت

                    order.status = 'paid'  # تغییر وضعیت سفارش خریدار به پرداخت‌شده
                    order.save()  # ذخیره تغییرات وضعیت سفارش

                return Response({
                    "detail": "پرداخت با موفقیت انجام و تایید شد و موجودی انبار بروزرسانی کردید.",
                    "ref_id": ref_id,
                    "order_id": order.id
                }, status=status.HTTP_200_OK)  # بازگرداندن پاسخ موفقیت‌آمیز به همراه شماره پیگیری و شماره سفارش

            else:
                payment.status = 'failed'  # تغییر وضعیت پرداخت به ناموفق در صورت عدم تایید بانک
                payment.save()  # ذخیره وضعیت ناموفق پرداخت
                return Response({
                    "detail": "تراکنش توسط درگاه تایید نشد.",
                    "errors": res_data.get('errors')
                }, status=status.HTTP_400_BAD_REQUEST)  # بازگرداندن خطای تایید نشدن تراکنش همراه با جزییات خطا از بانک

        except ValueError as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)  # مدیریت و بازگرداندن خطای عدم موجودی انبار با کد وضعیت ۴۰۰

        except requests.exceptions.RequestException as e:
            return Response({"detail": f"خطا در استعلام از درگاه: {str(e)}"},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)  # مدیریت خطاهای شبکه یا قطعی سرور درگاه با کد وضعیت ۵۰۳

