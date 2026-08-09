"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# schema_view = get_schema_view(
#     openapi.Info(
#         title="مستندات ای پی آی فروشگاه (Store API)",
#         default_version='v1',
#         description="مستندات کامل تمام اندپوینتهای سیستم فروشگاهی شامل احراز هویت، سبد خرید، سفارشات و پرداخت",
#         terms_of_service="https://www.google.com/policies/terms/",
#         contact=openapi.Contact(email="contact@mystore.local"),
#         license=openapi.License(name="BSD License")
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
# )
# schema_view.security = [{'Bearer': []}]

from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.securityDefinitions = {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': "<your_token> فرمت ورود توکن: Bearer"
            }
        }
        return schema

schema_view = get_schema_view(
    openapi.Info(
        title="مستندات ای پی آی فروشگاه (Store API)",
        default_version='v1',
        description="مستندات کامل تمام اندپوینتهای سیستم فروشگاهی شامل احراز هویت، سبد خرید، سفارشات و پرداخت",
    ),
    public=True,
    permission_classes=[permissions.AllowAny,],
    generator_class=JWTSchemaGenerator,
    authentication_classes=[],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/store/', include('products.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/coupons/', include('coupons.urls', namespace='coupons')),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc'), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
