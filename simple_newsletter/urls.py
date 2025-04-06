from django.urls import path
from . import views

app_name = "newsletter"


urlpatterns = [
    path("validate_email/", views.validate_email, name="validate-email"),
    path("unsubscribe/<str:email>/", views.unsubscribe, name="unsubscribe"),
    path("subscribe/", views.subscribe, name="subscribe"),
]
