from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from coupons.models import Coupon
from cart.cart import RedisCart
from .serializers import CouponApplySerializer

class CouponApplyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(request_body=CouponApplySerializer)
    def post(self, request):
        serializer = CouponApplySerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['code']
            now = timezone.now()

            try:
                coupon = Coupon.objects.get(
                    code__iexact=code,
                    valid_from__lte=now,
                    valid_to__gte=now,
                    active=True
                )

                cart = RedisCart(request)
                cart.apply_coupon(coupon)

                return Response(
                    {
                            "message": 'کد تخفیف با موفقیت اعمال شد.',
                            "discount_percent": coupon.discount
                        },
                        status=status.HTTP_200_OK
                )

            except Coupon.DoesNotExist:
                return Response(
                        {"error": "کد تخفیف معتبر نیست یا منقضی شذه است."},
                        status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)