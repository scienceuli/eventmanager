from django.contrib import admin

from mapbox_location_field.admin import MapAdmin

from .models import (
    EventCategory,
    Event,
    EventImage,
)

class EventImageInline(admin.StackedInline):
    model = EventImage

class EventAdmin(admin.ModelAdmin):
    inlines = (EventImageInline, )

admin.site.register(EventCategory)
admin.site.register(Event, EventAdmin)
