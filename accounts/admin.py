from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'phone_number', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('اطاعات اختصاصی',{'fields': ('phone_number',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('اطاعات اختصاصی', {'fields': ('email', 'phone_number',)}),
    )
