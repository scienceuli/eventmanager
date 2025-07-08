from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView


from users.views import login_page, logout_page
from users.forms import EmailValidationOnForgotPassword
from .forms import LoginForm, PwdResetForm, PwdResetConfirmForm


app_name = "account"

urlpatterns = [
    # path("login/", login_page, name="login"),
    # path("logout/", logout_page, name="logout"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="users/login.html", form_class=LoginForm),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/account/login/"), name="logout"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="users/password_reset.html",
            success_url="password_reset_email_confirm",
            email_template_name="users/password_reset_email.html",
            form_class=PwdResetForm,
        ),
        name="pwdreset",
    ),
    path(
        "password_reset_confirm/<uidb64>/<token>",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url="password_reset_complete/",
            form_class=PwdResetConfirmForm,
        ),
        name="password_reset_confirm",
    ),
    path(
        "password_reset/password_reset_email_confirm/",
        TemplateView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password_reset_complete/",
        TemplateView.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),

]
