from django.shortcuts import render

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

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
        context = super().get_context_data(**kwargs)
        event_queryset = Event.objects.order_by('start_date')

        # Version 1
        events_dict = {}

        for year, group in itertools.groupby(event_queryset, lambda e: e.start_date.strftime('%Y')):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(group, lambda e: e.start_date.strftime('%B')):
                events_dict[year][month] = list(inner_group)

        print(events_dict)

        # Version 2
        events_grouped_generator = itertools.groupby(
            event_queryset,
            lambda e: (e.start_date.strftime('%Y'),e.start_date.strftime('%B'))
        )

        events_grouped_list = [(grouper, list(values)) for grouper, values in events_grouped_generator]
        print(events_grouped_list)

        # context['events_grouped_list'] = events_grouped_list
        context['events_dict'] = events_dict
        return context

class EventCreateView(LoginRequiredMixin, CreateView):
    pass  

class EventUpdateView(LoginRequiredMixin, UpdateView):
    pass

class EventDetailView(LoginRequiredMixin, DetailView):
    pass

class EventDeleteView(LoginRequiredMixin, DeleteView):
    pass

class EventCategoryListView(LoginRequiredMixin, ListView):
    pass

class EventCategoryCreateView(LoginRequiredMixin, CreateView):
    pass

def search_event(request):
    if request.method == 'POST':
       data = request.POST['search']
       events = Event.objects.filter(name__icontains=data)
       context = {
           'events': events
       }
       return render(request, 'events/event_list.html', context)
    return render(request, 'events/event_list.html')