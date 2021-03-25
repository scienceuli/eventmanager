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
        '''
        ordnet die Teilnehmer-Auswahl einer Veranstaltung zu,
        die Teilnehmer werden aber noch nicht eingeschrieben.
        Die Action dient lediglich als Copy-Action bekannter Moodle-User-Daten
        zu einer Veranstaltung.
        '''
        if 'apply' in request.POST:
            event_id = request.POST["event"]
            event = Event.objects.get(id=event_id)
            # Teilnehmer anlegen 
            # der queryset enthält die ausgewählten User, also:
            for user in queryset:
                event.members.update_or_create(email=user.email,
                defaults={
                    'firstname': user.firstname,
                    'lastname': user.lastname
                })
            # alert zu dieser Aktion
            self.message_user(request, f"{len(queryset)} Teilnehmer*in(nen) wurde(n) der Veranstaltung {event.name} hinzugefügt.")
            return HttpResponseRedirect(request.get_full_path())

        form = EventForm(initial={'_selected_action': queryset.values_list('id', flat=True)})
        return render(request, "admin/event_choose.html", {'items': queryset, 'form': form})


