from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns

from django_otp.admin import AdminSite

from django.conf import settings

import private_storage.urls

# from .views import dashboard, login_page, logut_page
from events.views import admin_event_pdf

# 2FA / OTP
from django_otp.admin import OTPAdminSite

# admin.site.__class__ = OTPAdminSite


urlpatterns = [
    # path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
    # path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path("grappelli/", include("grappelli.urls")),  # grappelli URLS
    path("admin/", admin.site.urls),
    # path("admin/", admin_site.urls),
    path("users/", include("users.urls")),
    # path(
    #     "accounts/login/",
    #     auth_views.LoginView.as_view(template_name="users/login.html"),
    #     name="login",
    # ),
    # path('register/',user_views.register,name='register'),
    path("", include("events.urls")),
    path("private-media/", include(private_storage.urls)),
    path("faqs/", include("faqs.urls")),
    path("shop/", include("shop.urls")),
    path("payment/", include("payment.urls")),
    path("reports/", include("reports.urls")),
    path("paypal/", include("paypal.standard.ipn.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("<int:event_id>/pdf/", admin_event_pdf, name="admin-event-pdf"),
    re_path(r"hitcount/", include(("hitcount.urls", "hitcount"), namespace="hitcount")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
