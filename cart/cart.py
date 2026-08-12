import redis
import json
from django.conf import settings
from products.models import Product

# اتصال به دیتابیس ردیس (مطمئن شو کانفیگ‌های REDIS در settings برقرار است)
redis_client = redis.StrictRedis(
    host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=True  # برای اینکه خروجی‌ها به جای bytes به صورت string باشند
)


class RedisCart:
    def __init__(self, request):
        """
        تشخیص هویت کاربر برای ساخت کلید اختصاصی در ردیس
        """
        self.request = request
        if request.user.is_authenticated:
            # اگر کاربر لاگین بود، از ID او استفاده می‌کنیم
            self.cart_id = f"cart:{request.user.id}"
        else:
            # اگر مهمان بود، از session_key مرورگر استفاده می‌کنیم
            if not request.session.session_key:
                request.session.create()
            self.cart_id = f"cart:{request.session.session_key}"

    def add(self, product, quantity=1, override_quantity=False):
        """
        اضافه کردن محصول به سبد خرید یا تغییر تعداد آن
        """
        product_id = str(product.id)

        # ابتدا بررسی می‌کنیم آیا این محصول از قبل در سبد خرید ردیس هست؟
        item_data = redis_client.hget(self.cart_id, product_id)

        if item_data:
            item = json.loads(item_data)
            if override_quantity:
                item['quantity'] = quantity
            else:
                item['quantity'] += quantity
        else:
            # اگر محصول جدید بود، ساختار اولیه آن را می‌سازیم
            item = {
                'quantity': quantity,
                'price': str(product.price)  # قیمت را استرینگ ذخیره می‌کنیم تا فرمت دقیق حفظ شود
            }

        # ذخیره مجدد در دیتای Hash ردیس
        redis_client.hset(self.cart_id, product_id, json.dumps(item))
        # قرار دادن منقضی شدن خودکار (مثلاً سبد خرید بعد از ۷ روز پاک شود)
        redis_client.expire(self.cart_id, 604800)

    def remove(self, product):
        """
        حذف کامل یک محصول از سبد خرید
        """
        product_id = str(product.id)
        redis_client.hdel(self.cart_id, product_id)

    def __iter__(self):
        """
        پیمایش (Loop) روی آیتم‌های سبد خرید و متصل کردن آن‌ها به مدل واقعی Product در Postgres
        """
        cart_data = redis_client.hgetall(self.cart_id)
        product_ids = cart_data.keys()

        # خواندن یکجای تمام محصولات موجود در سبد خرید از دیت دیتابیس برای بهینه‌سازی (Avoid N+1 Query)
        products = Product.objects.filter(id__in=product_ids)

        # ساخت یک کپی از دیتای ردیس برای اضافه کردن شیء محصول به آن
        cart_clean = {}
        for p_id, data in cart_data.items():
            cart_clean[p_id] = json.loads(data)

        for product in products:
            p_id = str(product.id)
            cart_clean[p_id]['product'] = product
            cart_clean[p_id]['total_price'] = float(cart_clean[p_id]['price']) * cart_clean[p_id]['quantity']
            yield cart_clean[p_id]

    def __len__(self):
        """
        محاسبه تعداد کل کالاها در سبد خرید
        """
        cart_data = redis_client.hgetall(self.cart_id)
        return sum(json.loads(data)['quantity'] for data in cart_data.values())

    def get_total_price(self):
        """
        محاسبه قیمت کل سبد خرید
        """
        cart_data = redis_client.hgetall(self.cart_id)
        return sum(float(json.loads(data)['price']) * json.loads(data)['quantity'] for data in cart_data.values())

    def clear(self):
        """
        پاک کردن کامل سبد خرید (مثلاً بعد از پرداخت موفق)
        """
        redis_client.delete(self.cart_id)
