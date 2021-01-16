from django.urls import path

from .views import (
    EventListView,
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
    event_add_member_success_view,
)

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('event_list/', EventListView.as_view(), name='event-list'),
    path('event-create/', EventCreateView.as_view(), name='event-create'),
    path('category-list/', EventCategoryListView.as_view(), name='event-category-list'),
    path('create-category/', EventCategoryCreateView.as_view(), name='create-event-category'),
    path('event/<int:pk>/edit/', EventUpdateView.as_view(), name='event-edit'),
    path('detail/<int:pk>', EventDetailView.as_view(), name='event-detail'),
    path('delete/<int:pk>', EventDeleteView.as_view(), name='event-delete'),
    path('event_add_member/<int:pk>', event_add_member, name='event-add-member'),
    path('event_add_member_success/', event_add_member_success_view, name='event-add-member-success'),
    path('search_event/', search_event, name='search-event'),
    path('moodle_list/', moodle, name='moodle-list'),
]

