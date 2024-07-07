from django.urls import path
from django.contrib.auth import views as auth_views


from users.views import login_page, logout_page
from users.forms import EmailValidationOnForgotPassword


app_name = "users"

urlpatterns = [
    path("login/", login_page, name="login"),
    path("logout/", logout_page, name="logout"),
]
