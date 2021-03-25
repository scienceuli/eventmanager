from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect

from moodle.models import MoodleUser
from events.models import Event
from moodle.forms import EventForm



@admin.register(MoodleUser)
class MoodleUserAdmin(admin.ModelAdmin):
    list_display = ['lastname', 'firstname', 'email', 'moodle_id']
    actions = ['add_to_event']

    def add_to_event(self, request, queryset):
        if 'apply' in request.POST:
            event_id = request.POST["event"]
            event = Event.objects.get(id=event_id)
            return HttpResponseRedirect(request.get_full_path())

        form = EventForm(initial={'_selected_action': queryset.values_list('id', flat=True)})
        return render(request, "admin/event_choose.html", {'items': queryset, 'form': form})


