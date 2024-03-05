from django.urls import path
from django.contrib.auth import views as auth_views


from users.views import login_page, logout_page
from users.forms import EmailValidationOnForgotPassword


app_name = "users"

urlpatterns = [
    path("login/", login_page, name="login"),
    path("logout/", logout_page, name="logout"),
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
]
