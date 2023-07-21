from django.urls import path
from . import views

app_name = "faqs"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index-view"),
    path("<slug:slug>/", views.CategoryDetail.as_view(), name="category-detail"),
    path(
        "<slug:slug>/<slug:question>/",
        views.QuestionDetail.as_view(),
        name="question-detail",
    ),
]
