"""eventmanager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.urls import path, include, re_path
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns

from users import views as user_views
from django.contrib.auth import views as auth_views

from django.conf import settings

import private_storage.urls

# from .views import dashboard, login_page, logut_page
from events.views import admin_event_pdf

from users.forms import EmailValidationOnForgotPassword

urlpatterns = [
    # path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
    # path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path("grappelli/", include("grappelli.urls")),  # grappelli URLS
    path("admin/", admin.site.urls),
    path("login/", user_views.login_page, name="login"),
    path("logout/", user_views.logout_page, name="logout"),
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
    # path('register/',user_views.register,name='register'),
    path("", include("events.urls")),
    path("private-media/", include(private_storage.urls)),
    path("faqs/", include("faqs.urls")),
    path("shop/", include("shop.urls")),
    path("payment/", include("payment.urls")),
    path("paypal/", include("paypal.standard.ipn.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("<int:event_id>/pdf/", admin_event_pdf, name="admin-event-pdf"),
    re_path(r"hitcount/", include(("hitcount.urls", "hitcount"), namespace="hitcount")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
