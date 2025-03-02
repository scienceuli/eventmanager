from django.urls import path
from mailings.views import view_emails

app_name = "mailings"

urlpatterns = [
    path("admin/dev-emails/", view_emails, name="view-emails"),
]
