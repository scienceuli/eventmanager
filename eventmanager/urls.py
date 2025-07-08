from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views

from users.forms import EmailValidationOnForgotPassword

from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib.sitemaps.views import sitemap

from django.conf import settings

import private_storage.urls

# from .views import dashboard, login_page, logut_page
from events.views import admin_event_pdf
from events.sitemaps import EventSitemap

# 2FA
from two_factor.urls import urlpatterns as tf_urls
# from two_factor.admin import AdminSiteOTPRequired


# admin_site = OTPAdmin(name='OTPAdmin')
# admin_site.register(User)
# admin_site.register(TOTPDevice, TOTPDeviceAdmin)

# admin.site.__class__ = AdminSiteOTPRequired


sitemaps = {
    "events": EventSitemap,
}

# admin settings
admin.site.site_header = 'VFLL Veranstaltungskalender'                
admin.site.index_title = 'Admin'                 
admin.site.site_title = 'FOBI DEV' 


urlpatterns = [
    path("__reload__/", include("django_browser_reload.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("admin/", admin.site.urls),
    path("", include("events.urls")),
    path('', include(tf_urls)),
    path("account/", include("users.urls")),
    # path("account/", include("django.contrib.auth.urls")),
    # path(
    #     "accounts/login/",
    #     auth_views.LoginView.as_view(template_name="users/login.html"),
    #     name="login",
    # ),
    # path('register/',user_views.register,name='register'),
    # path(
    #     "password_reset/",
    #     auth_views.PasswordResetView.as_view(
    #         form_class=EmailValidationOnForgotPassword,
    #         from_email="password-reset@vfll.de",
    #         template_name="users/password_reset.html",
    #         email_template_name="users/password_reset_email.html",
    #     ),
    #     name="password_reset",
    # ),
    # path(
    #     "password_reset_done/",
    #     auth_views.PasswordResetDoneView.as_view(
    #         template_name="users/password_reset_done.html"
    #     ),
    #     name="password_reset_done",
    # ),
    # path(
    #     "reset/<uidb64>/<token>/",
    #     auth_views.PasswordResetConfirmView.as_view(
    #         template_name="users/password_reset_confirm.html"
    #     ),
    #     name="password_reset_confirm",
    # ),
    # path(
    #     "reset/done/",
    #     auth_views.PasswordResetCompleteView.as_view(
    #         template_name="users/password_reset_complete.html"
    #     ),
    #     name="password_reset_complete",
    # ),
    

    path("private-media/", include(private_storage.urls)),
    path("faqs/", include("faqs.urls")),
    path("shop/", include("shop.urls")),
    path("payment/", include("payment.urls")),
    path("reports/", include("reports.urls")),
    path("paypal/", include("paypal.standard.ipn.urls")),
    path("mailings/", include("mailings.urls")),
    path("vfllnl/", include("vfllnl.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("<int:event_id>/pdf/", admin_event_pdf, name="admin-event-pdf"),
    re_path(r"hitcount/", include(("hitcount.urls", "hitcount"), namespace="hitcount")),
    path(
        "export_action/",
        include("admin_export_action.urls", namespace="admin_export_action"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
