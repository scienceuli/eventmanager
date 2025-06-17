from django.urls import path
from . import views

app_name = "newsletter"


urlpatterns = [
    path("validate_email/", views.validate_email, name="validate-email"),
    #path("unsubscribe/<str:email>/", views.unsubscribe, name="unsubscribe"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path('subscribe/confirm/', views.subscription_confirmation, name='subscription_confirmation'),
    path('unsubscribe/', views.unsubscribe, name='unsubscribe'),
    path("create/", views.create_newsletter, name="create-newsletter"),
    path("send/<int:pk>/", views.send_newsletter, name="send-newsletter"),
    path('newsletters/', views.newsletter_list, name='newsletter-list'),
    path('edit/<int:pk>/', views.edit_newsletter, name='edit-newsletter'),
    path('copy/<int:pk>/', views.copy_newsletter, name='copy-newsletter'),
    path('delete/<int:pk>/', views.delete_newsletter, name='delete-newsletter'),
    path('preview/<int:pk>/', views.preview_newsletter, name='preview-newsletter'),
]
