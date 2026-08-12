from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product

@receiver(post_save, sender=Product)
def clear_product_cache_on_save(sender, instance, **kwargs):
    cache.delete(f"product_detail_{instance.id}")
    if instance.slug:
        cache.delete(f"product_detail_{instance.slug}")

    cache.delete(f"product_list_all")
    print(f"Signals: Cache cleared for product {instance.id} / {instance.slug}")

@receiver(post_delete, sender=Product)
def clear_product_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f"product_detail_{instance.id}")
    if instance.slug:
        cache.delete(f"product_detail_{instance.slug}")
    cache.delete(f"product_list_all")
    print(f"Signals: Cache cleared due to product deletion")