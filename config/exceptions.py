from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

# ایجاد لاگر اختصاصی
logger = logging.getLogger('django')


def custom_exception_handler(exc, context):
    # فراخوانی هندلر استاندارد DRF
    response = exception_handler(exc, context)

    # اگر خطای غیرمنتظره‌ای پیش اومده باشه که DRF نسناستش (ارورهای ۵۰۰ سرور)
    if response is None:
        view_name = context['view'].__class__.__name__
        logger.error(f"Internal Server Error in {view_name}: {str(exc)}", exc_info=True)

        return Response(
            {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "InternalServerError",
                "message": "یک خطای داخلی در سرور رخ داده است. لطفاً بعداً تلاش کنید."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # اگر خطاهای شناخته شده DRF باشه (مثل ۴۰۴، ۴۰۳، ۴۰۰ و ۴۲۹)
    custom_response_data = {
        "status_code": response.status_code,
        "error": exc.__class__.__name__,
        "message": response.data.get('detail', response.data)
    }

    response.data = custom_response_data
    return response
