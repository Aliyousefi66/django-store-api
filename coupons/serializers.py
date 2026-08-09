from rest_framework import serializers

class CouponApplySerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=50)