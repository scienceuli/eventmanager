from django.urls import path
from . import views

app_name = "newsletter"


urlpatterns = [
    path("unsubscribe/<str:email>/", views.unsubscribe, name="unsubscribe"),
]
