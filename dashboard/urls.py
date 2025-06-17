from django.urls import path, include, re_path

from .views import dashboard, dashboard_stats, view_invoice_pdf, event_autocomplete, members_list

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("stats/", dashboard_stats, name="dashboard-stats"),
    path('invoice/<int:invoice_id>/', view_invoice_pdf, name='view-invoice-pdf'),
    path('event-autocomplete/', event_autocomplete, name='event-autocomplete'),
    path('members/', members_list, name='members-list'),
]
