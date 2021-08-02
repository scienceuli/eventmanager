from django.urls import path

from .views import (
    EventListView,
    EventMemberDetailView,
    FilteredEventListView,
    EventCreateView,
    EventCategoryListView,
    EventCategoryCreateView,
    EventUpdateView,
    EventDetailView,
    EventDeleteView,
    search_event,
    moodle,
    home,
    dashboard,
    event_add_member,
    get_moodle_data,
    EventApi,
    EventMembersListView,
    EventMemberDetailView,
    export_members_csv,
    members_dashboard_view,
)

# sentry test
def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("sentry-debug/", trigger_error),  # sentry test
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("event_list/", EventListView.as_view(), name="event-list"),
    path("event_filter/", FilteredEventListView.as_view(), name="event-filter"),
    path("event-create/", EventCreateView.as_view(), name="event-create"),
    path("category-list/", EventCategoryListView.as_view(), name="event-category-list"),
    path(
        "create-category/",
        EventCategoryCreateView.as_view(),
        name="create-event-category",
    ),
    path("event/<int:pk>/edit/", EventUpdateView.as_view(), name="event-edit"),
    path("detail/<slug:slug>", EventDetailView.as_view(), name="event-detail"),
    path("delete/<int:pk>", EventDeleteView.as_view(), name="event-delete"),
    path("event_add_member/<slug:slug>", event_add_member, name="event-add-member"),
    path("search_event/", search_event, name="search-event"),
    path("moodle_list/", moodle, name="moodle-list"),
    path("get_moodle_data/", get_moodle_data, name="get-moodle-data"),
    path("events-api/", EventApi.as_view(), name="Event"),
    path("members/<event>/", EventMembersListView.as_view(), name="members"),
    path(
        "members/detail/<int:pk>/",
        EventMemberDetailView.as_view(),
        name="member-detail",
    ),
    path("members/export/csv/", export_members_csv, name="export-members-csv"),
    path("members_dashboard/", members_dashboard_view, name="members-dashboard"),
]
