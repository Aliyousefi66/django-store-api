from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework.views import APIView
from .serializers import RegisterSerializer, UserProfileSerializer, SendOTPSerializer, VerifyOTPSerializer
import random
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework import status
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