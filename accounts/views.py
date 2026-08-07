from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework.views import APIView
from .serializers import RegisterSerializer, UserProfileSerializer, SendOTPSerializer, VerifyOTPSerializer
import random
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

# class RegisterView(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = str(random.randint(1000,9999))
            cache.set(phone_number, otp_code, timeout=120)

            print(f"===============================================")
            print(f"OTP Code for {phone_number} is: {otp_code}")
            print(f"===============================================")

            return Response(
                {"detail": "کد یکبار مصرف با موفقیت ارسال شد."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user_code = serializer.validated_data['code']

            cached_code = cache.get(phone_number)

            if cached_code is None:
                return Response({"detail": "کد یکبار مصرف منقضی شده یا ارسال نشده است."}, status=status.HTTP_400_BAD_REQUEST)

            if cached_code != user_code:
                return Response({"detail": "کد وارد شده اشتباه است."}, status=status.HTTP_400_BAD_REQUEST)

            cache.delete(phone_number)

            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'username': phone_number}
            )

            refresh = RefreshToken.for_user(user)

            return Response({
                "detail": "ورود با موفقیت انجام شد.",
                "created_now_user": created,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestEmailVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.email:
            return Response({"detail": "ابتدا باید ایمیل خود را در پروفایل ثبت کنید."}, status=status.HTTP_400_BAD_REQUEST)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        activation_link = f"http://127.0.0.1:8000/api/accounts/verify_email/{uid}/{token}/"

        subject = "تاییذ ایمیل حساب کاربری"
        message = f"سلام {user.username} عزیز،\n\nلطفاً برای تأیید ایمیل خود روی لینک زیر کلیک کنید:\n{activation_link}"

        try:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email='no-reply@mystore.com',
                to=[user.email],
            )
            email.encoding = 'utf-8'
            email.send(fail_silently=False)

            return Response({"detail": "لینک فعال سازی با موفقیت به ایمیل شما ارسال شد."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "خطا در ارسال ایمیل، لطفا بعدا تلاش کنید."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"detail": "ایمیل شما با موفقیت تایید و فعال شد."}, status=status.HTTP_200_OK)
        return Response({"detail": "لینک فغال سازی نامعتبر است یا منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)