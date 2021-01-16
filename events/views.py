from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

from django.core.mail import send_mail, BadHeaderError

from django.conf import settings

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)
from .models import (
    EventCategory,
    Event,
    EventImage,
)

from .forms import EventMemberForm

from .api import call

from .utils import send_email

import itertools

def home(request):
    return render(request, 'events/home.html')

@login_required(login_url='login')
def dashboard(request):
    event_ctg_count = EventCategory.objects.count()
    event_count = Event.objects.count()
    events = Event.objects.all()
    context = {
        'event_ctg_count': event_ctg_count,
        'event_count': event_count,
        'events': events
    }
    return render(request, 'events/dashboard.html', context)

class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    
    def get_context_data(self, **kwargs):
        # get moodle courses
        fname = 'core_course_get_courses'
        courses_list = call(fname)

        # events from database
        context = super().get_context_data(**kwargs)
        event_queryset = Event.objects.order_by('start_date')
        
        if self.request.GET.get('cat'):
            event_queryset = event_queryset.filter(category__name=self.request.GET.get('cat'))

        # Version 1
        events_dict = {}

        for year, group in itertools.groupby(event_queryset, lambda e: e.start_date.strftime('%Y')):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(group, lambda e: e.start_date.strftime('%B')):
                events_dict[year][month] = list(inner_group)

        print(events_dict)


        # context['events_grouped_list'] = events_grouped_list
        context['events_dict'] = events_dict
        return context

class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    fields = ['name', ]
    template_name = 'events/create_event.html'

class EventUpdateView(LoginRequiredMixin, UpdateView):
    pass

class EventDetailView(LoginRequiredMixin, DetailView):
    login_url = 'login'
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

class EventDeleteView(LoginRequiredMixin, DeleteView):
    pass

class EventCategoryListView(LoginRequiredMixin, ListView):
    
    login_url = 'login'
    model = EventCategory
    template_name = 'events/event_category.html'
    context_object_name = 'event_category'

class EventCategoryCreateView(LoginRequiredMixin, CreateView):
    login_url = 'login'
    model = EventCategory
    fields = ['name',]
    template_name = 'events/create_event_category.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)

def search_event(request):
    if request.method == 'POST':
       data = request.POST['search']
       event_queryset = Event.objects.filter(name__icontains=data)
       
       events_dict = {}
       
       for year, group in itertools.groupby(event_queryset, lambda e: e.start_date.strftime('%Y')):
           events_dict[year] = {}
           for month, inner_group in itertools.groupby(group, lambda e: e.start_date.strftime('%B')):
               events_dict[year][month] = list(inner_group)
           context = {
               'events_dict': events_dict
           }
       return render(request, 'events/event_list.html', context)
    return render(request, 'events/event_list.html')


def event_add_member(request, pk):
    event = get_object_or_404(Event, pk=pk)
    template_name = 'anmeldung'

    if request.method == 'GET':
        form = EventMemberForm()
    else:
        form = EventMemberForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            address = form.cleaned_data['address']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            message = form.cleaned_data['message']
            subject=f"Anmeldung am Kurs {event.name}"
            formatting_dict = {
                'name': name,
                'address': address,
                'email': email,
                'phone': phone,
                'event': event.name,
                'start': event.start_date,
                'end': event.end_date,
            }
            try:
                addresses = {'to': [settings.EVENT_RECEIVER_EMAIL]}
                send_email(addresses, subject, template_name, formatting_dict=formatting_dict)
                messages.success(request, 'Vielen Dank für Ihre Anmeldung. Wir melden uns bei Ihnen.')
            except BadHeaderError:
                return HttpResponse('Invalid header found.')
            return redirect('event-detail', event.id)
    return render(request, "events/add_event_member.html", {'form': form, 'event': event})

def event_add_member_success_view(request):
    return HttpResponse('Success! Thank you for your message.')


# moodle
def moodle(request):
    fname = 'core_course_get_courses'
    courses_list = call(fname)
    context = {
        'courses': courses_list
    }
    return render(request, 'events/moodle_list.html', context)