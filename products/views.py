from django.db.models import Q
from rest_framework import generics, filters, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

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

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = 'slug'