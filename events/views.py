from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone


from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

from django.core.mail import send_mail, BadHeaderError

from django.conf import settings
#

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
    EventMember,
)

from .forms import EventMemberForm

from .api import call

from .utils import send_email

import itertools

from wkhtmltopdf.views import PDFTemplateResponse

import locale
# for German locale
locale.setlocale(locale.LC_TIME, "de_DE") 


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
    template_name = 'events/event_list_tw.html'
    
    def get_context_data(self, **kwargs):
        # get moodle courses
        #fname = 'core_course_get_courses'
        #courses_list = call(fname)

        # events from database
        context = super().get_context_data(**kwargs)
        event_queryset_unsorted = Event.objects.all().exclude(event_days=None) # unsorted
        
        event_queryset = sorted(event_queryset_unsorted, key=lambda t: t.get_first_day_start_date())
        
        if self.request.GET.get('cat'):
            event_queryset = sorted(event_queryset_unsorted.filter(category__name=self.request.GET.get('cat')), key=lambda t: t.get_first_day_start_date())

        # Version 1
        events_dict = {}

        for year, group in itertools.groupby(event_queryset, lambda e: e.get_first_day_start_date().strftime('%Y')):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(group, lambda e: e.get_first_day_start_date().strftime('%B')):
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
    template_name = 'events/event_detail_tw.html'
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
       return render(request, 'events/event_list_tw.html', context)
    return render(request, 'events/event_list_tw.html')

@login_required(login_url='login')
def event_add_member(request, slug):
    event = get_object_or_404(Event, slug=slug)
    template_name = 'anmeldung'

    if request.method == 'GET':
        form = EventMemberForm()
    else:
        form = EventMemberForm(request.POST)
        if form.is_valid():
            firstname = form.cleaned_data['firstname']
            lastname = form.cleaned_data['lastname']

            address_line = form.cleaned_data['address_line']
            street = form.cleaned_data['street']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            postcode = form.cleaned_data['postcode']

            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            message = form.cleaned_data['message']
            vfll = form.cleaned_data['vfll']
            memberships = form.cleaned_data['memberships']
            attention = form.cleaned_data['attention']
            attention_other = form.cleaned_data['attention_other']
            education_bonus = form.cleaned_data['education_bonus']
            check = form.cleaned_data['check']

            # make name of this registration from event label and date

            name = f"{event.label} | {timezone.now()}"

            new_member = EventMember.objects.create(
                name=name, 
                event=event,
                firstname=firstname,
                lastname=lastname,
                street=street,
                address_line=address_line,
                city=city,
                postcode=postcode,
                state=state,
                email=email,
                phone=phone,
                message=message,
                vfll=vfll,
                memberships=memberships,
                attention=attention,
                attention_other=attention_other,
                education_bonus=education_bonus,
                check=check,
                attend_status="registered",
            )

            '''
            zusätzlich wird ein eindeutiges Label für diese Anmeldun kreiert, um das Label
            für Mailversand zu haben.
            Das wird in in models.py in der save method hinzugefügt
            '''
            
            member_label = EventMember.objects.latest('date_created').label

            # msil preparation
            subject=f"Anmeldung am Kurs {event.name}"
            formatting_dict = {
                'firstname': firstname,
                'lastname': lastname,
                'address_line': address_line,
                'street': street,
                'city': city,
                'postcode': postcode,
                'state': state,
                'email': email,
                'phone': phone,
                'event': event.name,
                'label': event.label,
                'start': event.start_date,
                'end': event.end_date,
                'member_label': member_label
            }

            try:
                addresses = {'to': [settings.EVENT_RECEIVER_EMAIL]}
                send_email(addresses, subject, template_name, formatting_dict=formatting_dict)
                messages.success(request, 'Vielen Dank für Ihre Anmeldung. Wir melden uns bei Ihnen.')
                new_member = EventMember.objects.latest('date_created')
                new_member.mail_to_admin = True
                new_member.save()

            except BadHeaderError:
                return HttpResponse('Invalid header found.')
                
            return redirect('event-detail', event.slug)
    return render(request, "events/add_event_member_tw.html", {'form': form, 'event': event})




# moodle
def moodle(request):
    fname = 'core_course_get_courses'
    courses_list = call(fname)
    context = {
        'courses': courses_list
    }
    return render(request, 'events/moodle_list.html', context)

@login_required(login_url='login')
def get_moodle_data(request):
    get_and_save_courses_from_moodle.delay()
    return HttpResponse('moodle Daten aktualisiert')


def admin_event_pdf(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    context = {
        'event': event
    }
    response = PDFTemplateResponse(
        request=request,
        context=context,
        template='admin/event_pdf_template.html',
        filename="event.pdf",
        show_content_in_browser=True,
        cmd_options={
            'encoding': 'utf8',
            'quiet': True,
            'orientation': 'portrait',
        }
    )

    return response
    

