import requests
import json
import datetime

from django.conf import settings

from events.warnings import Warning
from events.exception import MoodleException

from django.core.management.base import BaseCommand

from events.models import EventSpeaker, EventLocation, EventCategory, EventFormat, Event

def get_timestamp(timestamp):
    try:
        #assume, that timestamp is given in seconds with decimal point
        ts = float(timestamp)
    except ValueError:
        return None
    return datetime.datetime.fromtimestamp(ts)


def safe_list_get(l, idx, key):
  try:
    return l[idx][key]
  except IndexError:
    return None

def call(fname, **kwargs):
    parameters = kwargs
    moodlewsrestformat = 'json'
    parameters.update({
        'wstoken': settings.MOODLE_SECRET,
        'moodlewsrestformat': moodlewsrestformat, 
        "wsfunction": fname,
    })
    response = requests.get(settings.MOODLE_URL+settings.MOODLE_ENDPOINT, parameters)

    if response.ok and moodlewsrestformat == 'json':
        data = response.json()
        return process_response(data)
    return response.text

def process_response(data):
    if type(data) == dict:
        if 'warnings' in data and data['warnings']:
            print('Warning')
        if 'exception' in data or 'errorcode' in data:
            print('exception in data')
    return data

def get_moodle_courses():
    # get moodle courses
    fname = 'core_course_get_courses'
    courses = call(fname)
    return courses
    
def get_moodle_course_enroled_users(course_id):
    fname = 'core_enrol_get_enrolled_users'
    course_dict = {
        'courseid': course_id,
    }
    course_enrolled_users = call(fname, **course_dict)
    return course_enrolled_users

def save_trainer_to_db(trainer_dict):
    if trainer_dict['trainer_exists']:
        obj, created = EventSpeaker.objects.get_or_create(
            email=trainer_dict['trainer_email'],
            defaults={
                'first_name': trainer_dict['trainer_firstname'],
                'last_name': trainer_dict['trainer_lastname'],
            } 
        )

def save_course_to_db(course_dict, trainer_dict):
    category = EventCategory.objects.get(name='Onlineseminare')
    eventformat = EventFormat.objects.get(name="Online")
    speaker = EventSpeaker.objects.get(email=trainer_dict['trainer_email'])
    location = EventLocation.objects.get(title='FOBI Moodle')
    obj, created = Event.objects.update_or_create(
        moodle_id=course_dict['moodle_id'],
        defaults={
            'category': category,
            'eventformat': eventformat,
            'name': course_dict['course_fullname'], 
            'label': course_dict['course_shortname'],
            'description': course_dict['course_summary'],
            'target_group': 'siehe Moodle', 
            'prerequisites': 'siehe Moodle',
            'objectives': 'siehe Moodle',
            'speaker': speaker,
            'scheduled_status': 'scheduled',
            'location': location,
            'fees': 'siehe Moodle', 
            'total_costs': 'siehe Moodle',
            'registration': 'siehe Moodle',
            'start_date': course_dict['course_start_date'],
            'end_date': course_dict['course_end_date'],
            'capacity': 20,
            'status': 'active',
            'students_number': course_dict['moodle_students_counter'],
        }
    )

def get_user_by_email(email):
    fname = 'core_user_get_users_by_field'
    course_dict = {
        'field': 'email',
        'values[0]': email
    }
    user = call(fname, **course_dict)
    return user

def enrol_user_to_course(email, course):
    #  check if user exists
    fname = 'enrol_manual_enrol_users'
    print(f"email: {email}")
    user = get_user_by_email(email)
    print(f"user: {user}")
    
    if user:
        user_id = user[0]['id']
        print(f"user_id: {user_id}")
    

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        courses = get_moodle_courses()
        id_list_of_moodle_courses = []
        for course in courses:
            #print(course['id'])
            id_list_of_moodle_courses.append(course['id'])
            #print(course['fullname'])
            #print(course['shortname'])
            #print(course['categoryid'])
            #print(course['startdate'])

        # get all moodle courses from database
        print(id_list_of_moodle_courses)
        moodle_courses_in_db = Event.objects.filter(moodle_id__gt=0).values_list('moodle_id', flat=True)

        moodle_id_list_from_db = list(moodle_courses_in_db)
        print(moodle_id_list_from_db)

        moodle_only_in_db_set = list(set(set(moodle_id_list_from_db) - set(id_list_of_moodle_courses)))
        print(moodle_only_in_db_set)

        # delete all courses only in db
        Event.objects.filter(moodle_id__in=moodle_only_in_db_set).delete()

        for course in courses:
            print(f"Kurs: {course['fullname']}")
            course_id = course['id']
            course_cat_id = course['categoryid']

            course_dict = {}
            course_dict['moodle_id'] = course_id
            course_dict['course_fullname'] = course['fullname']
            course_dict['course_shortname'] = course['shortname']
            course_dict['course_start_date'] = get_timestamp(course['startdate'])
            course_dict['course_end_date'] = get_timestamp(course['enddate'])
            if course['summary']:
                course_dict['course_summary'] = course['summary']
            else:
                course_dict['course_summary'] = "wird noch ergänzt"

            # get course users
            course_users = get_moodle_course_enroled_users(course_id)
            
            trainer_firstname=""
            trainer_lastname="NN"
            trainer_email="NN@nn.de"
            trainer_exists = False
            #initialize number of students (Teilnehmer)
            moodle_students_counter = 0
            for user in course_users:
                role_id = safe_list_get(user['roles'], 0, 'roleid')
                # print(f"role_id: {role_id}")
                if role_id == 3: # trainer
                    trainer_firstname = user['firstname']
                    trainer_lastname = user['lastname']
                    trainer_email = user['email']
                    trainer_exists = True
                elif role_id == 5: # students
                    moodle_students_counter += 1

            trainer_dict = {}
            trainer_dict['trainer_firstname'] = trainer_firstname
            trainer_dict['trainer_lastname'] = trainer_lastname
            trainer_dict['trainer_email'] = trainer_email
            trainer_dict['trainer_exists'] = trainer_exists

            course_dict['moodle_students_counter'] = moodle_students_counter

            '''
            nur die Kurse aus den Bereichen in Planung(id = 3) und 
            Fortbildungen (id=4) werden gespeichert
            '''
            if course_cat_id == 3 or course_cat_id == 4:
                save_trainer_to_db(trainer_dict)
                save_course_to_db(course_dict, trainer_dict)

            print(course_dict)
            print(trainer_dict)
            
            
            #print(f"Trainer: {trainer}")
                #if user['roles'][0]['roleid'] == 3:
                #    print(f"{user['fullname']} ({ser['roles'][0]['shortname']})")





'''

def course_detail(request, course_id):
    fname = 'core_course_get_courses'
    course_dict = {
        'options[ids][0]': course_id,
    }
    course_list = call(fname, **course_dict)
    
    fname = 'core_enrol_get_enrolled_users'
    course_dict = {
        'courseid': course_id,
    }
    course_enrolled_users = call(fname, **course_dict)

    context = {
        'course': course_list[0],
        'course_users': course_enrolled_users,
    }
    return render(request, 'moodle/course_detail.html', context)
'''