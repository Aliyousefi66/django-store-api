from urllib import response

from django.db.models import Q
from rest_framework import generics, filters, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

from django.core.cache import cache
from django.conf import settings

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductListView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ['name', 'description']

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        category_param = self.request.query_params.get('category')

        if category_param:
            queryset = queryset.filter(
                Q(category__slug=category_param) | Q(category__name__icontains=category_param)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        query_params = request.GET.urlencode()
        cache_key = f"product_list_{query_params}" if query_params else "product_list_all"

        cache_data = cache.get(cache_key)
        if cache_data:
            print("WOW! DATA CAME FROM REDIS CACHE!")
            return Response(cache_data)

        print("OOPS! HIT THE DATABASE (POSTGRES) ...")
        response = super().list(request, *args, **kwargs)

        timeout_value = getattr(settings, 'CACHE_TTL', 900)
        cache.set(cache_key, response.data, timeout=timeout_value)

        return response


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = 'slug'