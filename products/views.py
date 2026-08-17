from rest_framework import generics, filters, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(generics.ListCreateAPIView):
    """
    دریافت لیست دسته‌بندی‌ها با قابلیت کشینگ در Redis و امکان ایجاد دسته‌بندی جدید
    """
    queryset = Category.objects.all()  # دریافت تمام دسته‌بندی‌ها از دیتابیس
    serializer_class = CategorySerializer  # تعیین سریالایزر تبدیل دسته‌بندی به JSON
    authentication_classes = [JWTAuthentication]  # احراز هویت با توکن JWT
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # خواندن برای همه آزاد، ساخت فقط برای کاربران لاگین‌شده

    def list(self, request, *args, **kwargs):
        cache_key = "category_list"  # ساخت کلید اختصاصی و ثابت برای کش دسته‌بندی‌ها

        cached_data = cache.get(cache_key)  # جستجو برای یافتن لیست دسته‌بندی‌ها در Redis
        if cached_data:  # اگر داده در کش موجود بود
            return Response(cached_data)  # بازگرداندن پاسخ فوری از کش بدون اتصال به دیتابیس

        response = super().list(request, *args, **kwargs)  # خواندن دسته‌بندی‌ها از دیتابیس

        timeout_value = getattr(settings, 'CACHE_TTL', 900)  # دریافت زمان انقضای کش (پیش‌فرض ۱۵ دقیقه)
        cache.set(cache_key, response.data, timeout=timeout_value)  # ذخیره نتیجه در Redis

        return response  # بازگرداندن پاسخ نهایی

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)  # ساخت دسته‌بندی جدید در دیتابیس
        cache.delete("category_list")  # پاک‌کردن کش دسته‌بندی‌ها جهت به‌روزرسانی لیست برای کاربران
        return response  # بازگرداندن پاسخ ساخت دسته‌بندی


class ProductListView(generics.ListCreateAPIView):
    """
    ۱. دریافت لیست محصولات با کشینگ Redis و ایجاد محصول جدید
    """
    serializer_class = ProductSerializer # تعیین سریالایزر مورد استفاده برای تبدیل مدل به JSON
    filter_backends = [filters.SearchFilter] # فعال‌سازی قابلیت جستجو در DRF
    authentication_classes = [JWTAuthentication] # استفاده از احراز هویت با توکن JWT
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # دسترسی خواندن برای همه، ایجاد فقط برای کاربران لاگین‌شده
    search_fields = ['name', 'description'] # فیلدهایی که کاربر می‌تواند در آن‌ها جستجو کند (?search=)

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True) # انتخاب محصولات فعال از دیتابیس
        category_param = self.request.query_params.get('category') # دریافت پارامتر category از URL

        if category_param: # اگر پارامتر category فرستاده شده بود
            queryset = queryset.filter(
                Q(category__slug=category_param) | Q(category__name__icontains=category_param) # فیلتر بر اساس اسلاگ یا نام دسته‌بندی
            )
        return queryset # بازگرداندن کوئری فیلترشده

    def list(self, request, *args, **kwargs):
        query_params = request.GET.urlencode() # تبدیل تمام پارامترهای آدرس URL به یک رشته منحصربه‌فرد
        cache_key = f"product_list_{query_params}" if query_params else "product_list" # ساخت کلید اختصاصی برای کش Redis

        cache_data = cache.get(cache_key) # جستجو برای یافتن داده در کش Redis
        if cache_data: # اگر داده در Redis موجود بود
            print("WOW! DATA CAME FROM REDIS CACHE!") # چاپ پیغام لاگ موفقیت کش
            return Response(cache_data) # بازگرداندن فوری پاسخ از RAM بدون درگیر کردن دیتابیس

        print("OOPS! HIT THE DATABASE (POSTGRES) ...") # چاپ پیغام خواندن داده از دیتابیس اصلی
        response = super().list(request, *args, **kwargs) # خواندن اطلاعات از دیتابیس و اعمال لایه‌بندی (Pagination)

        timeout_value = getattr(settings, 'CACHE_TTL', 900) # دریافت زمان انقضای کش از تنظیمات (پیش‌فرض ۹۰۰ ثانیه)
        cache.set(cache_key, response.data, timeout=timeout_value) # ذخیره نتیجه دیتابیس در کش Redis

        return response # بازگرداندن پاسخ نهایی به کاربر

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs) # ثبت محصول جدید در دیتابیس
        cache.delete_pattern("product_list*") if hasattr(cache, 'delete_pattern') else cache.clear() # پاک‌کردن تمام کش‌های لیست محصولات پس از ایجاد محصول جدید
        return response # بازگرداندن پاسخ ساخت موفقیت‌آمیز محصول


class ProductDetailView(generics.RetrieveAPIView):
    """
    ۲. دریافت جزئیات یک محصول با قابلیت پشتیبانی از ID و Slug و کشینگ Redis
    """
    queryset = Product.objects.filter(is_active=True) # کوئری پایه برای دریافت محصولات فعال
    serializer_class = ProductSerializer # تعیین سریالایزر برای تبدیل محصول به JSON

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset()) # اعمال فیلترهای پایه روی کوئری
        lookup_value = self.kwargs.get('lookup') or self.kwargs.get('pk') or self.kwargs.get('slug') # استخراج پارامتر ورودی از آدرس URL

        if str(lookup_value).isdigit(): # بررسی اینکه آیا پارامتر ورودی عدد است (شناسه یا ID)
            obj = get_object_or_404(queryset, id=lookup_value) # دریافت محصول بر اساس ID یا ارسال خطای ۴۰۴
        else:
            obj = get_object_or_404(queryset, slug=lookup_value) # دریافت محصول بر اساس Slug یا ارسال خطای ۴۰۴

        self.check_object_permissions(self.request, obj) # بررسی سطوح دسترسی روی آبجکت پیدا شده
        return obj # بازگرداندن آبجکت محصول

    def retrieve(self, request, *args, **kwargs):
        lookup_value = kwargs.get('lookup') or kwargs.get('pk') or kwargs.get('slug') # گرفتن مقدار ورودی آدرس برای ساخت کلید کش
        cache_key = f"product_detail_{lookup_value}" # ساخت کلید کش اختصاصی برای جزئیات این محصول

        cache_data = cache.get(cache_key) # بررسی وجود جزئیات محصول در Redis
        if cache_data: # اگر در کش موجود بود
            print(f"PRODUCT {lookup_value} DETAILS CAME FROM REDIS CACHE!") # چاپ پیغام دریافت داده از کش
            return Response(cache_data) # بازگرداندن پاسخ از کش Redis

        print(f"HIT THE DATABASE FOR PRODUCT {lookup_value} ...") # چاپ پیغام خواندن جزئیات از دیتابیس (اصلاح متغیر)
        response = super().retrieve(request, *args, **kwargs) # خواندن جزئیات محصول از دیتابیس

        timeout_value = getattr(settings, 'CACHE_TTL', 900) # دریافت زمان انقضای کش
        cache.set(cache_key, response.data, timeout=timeout_value) # ذخیره جزئیات محصول در Redis

        return response # بازگرداندن پاسخ نهایی