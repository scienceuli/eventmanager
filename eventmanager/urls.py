from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from users.forms import EmailValidationOnForgotPassword

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
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            form_class=EmailValidationOnForgotPassword,
            from_email="password-reset@vfll.de",
            template_name="users/password_reset.html",
            email_template_name="users/password_reset_email.html",
        ),
        name="password_reset",
    ),
    path(
        "password_reset_done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="users/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
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
