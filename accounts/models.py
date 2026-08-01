from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_regex = RegexValidator(
    regex=r'^09\d{9}$',
    message="شماره تلفن باید 11 رقم بوده و با 09 شروع شود."
)

class CustomUser(AbstractUser):
    email = models.EmailField(
        unique=True,
        verbose_name='آدرس ایمیل',
        error_messages={
            'unique': "کاربری با این ایمیل قبلا ثبت نام کرده است."
        }
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True, null=True,
        verbose_name="شماره تلفن",
        unique=True,
    )
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")

    REQUIRED_FIELDS = ['email',]

    def __str__(self):
        return self.username or self.email
