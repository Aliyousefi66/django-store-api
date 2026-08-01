from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from accounts.models import phone_regex

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            phone_number=validated_data.get('phone_number', None),
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number')

phone_regex = RegexValidator(
    regex=r'^09\d{9}$',
    message="شماره تلفن باید 11 رقم و با 09 شروع شود."
)

class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=15)
    code = serializers.CharField(max_length=6, min_length=4)