from rest_framework.throttling import UserRateThrottle

class PaymentRateThrottle(UserRateThrottle):
    scope = 'payment' #  از نرخ 'payment' که در setting ست کردیم استفاده میکند (۵ بار در دقیقه)