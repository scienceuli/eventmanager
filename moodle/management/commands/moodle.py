import requests
import json
import datetime, pytz
import itertools

from django.conf import settings

from events.warnings import Warning
from events.exception import MoodleException

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from events.models import EventSpeaker, EventSpeakerThrough, EventLocation, EventCategory, EventFormat, Event, EventMember, MemberRole, EventMemberRole
from moodle.models import MoodleUser

# Roles Dict
roles_dict = {
    'MANAGER_ROLE_ID': 1,
    'TRAINER_ROLE_ID': 3,
    'STUDENT_ROLE_ID': 5
}



# test user
test_user_list = [f"user{str(i)}@elearning-and-more.de" for i in range(1, 7)]


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


def save_course_to_db(course_dict):
    category, _ = EventCategory.objects.get_or_create(name='Onlineseminare')

    try:
        location = Event.objects.get(moodle_id=course_dict['moodle_id']).location
    except:
        location, _ = EventLocation.objects.get_or_create(title='FOBI Moodle') 

    try:
        eventformat = Event.objects.get(moodle_id=course_dict['moodle_id']).eventformat
    except:
        eventformat, _ = EventFormat.objects.get_or_create(name="Online")  

    #print(f"location: {location}")
    obj, created = Event.objects.update_or_create(
        moodle_id=course_dict['moodle_id'],
        defaults={
            'category': category,
            'eventformat': eventformat,
            'name': course_dict['course_fullname'], 
            'label': course_dict['course_shortname'],
            #'description': course_dict['course_summary'],
            #'target_group': 'siehe Moodle', 
            #'prerequisites': 'siehe Moodle',
            #'objectives': 'siehe Moodle',
            #'scheduled_status': 'scheduled',
            'location': location,
            #'fees': 'siehe Moodle', 
            #'total_costs': 'siehe Moodle',
            #'registration': 'siehe Moodle',
            'start_date': course_dict['course_start_date'],
            'end_date': course_dict['course_end_date'],
            #'capacity': 20,
            #'status': 'active',
        }
    )
    # when course is created, enroled users can be stored
    save_course_enroled_users_to_db(course_dict['moodle_id'], obj)

def save_course_enroled_users_to_db(course_id, event):
    '''
    creates or updates or deletes enroled users from moodle in db
    users_dict: contains users data: firstname, lastname, email
    no bulk method used, which would be more efficient but harder to code
    updating moodle users is only background process per celery so efficiency  does not matter
    at this point
    '''
    # get users of course 
    users_and_teacher_list = get_moodle_course_enroled_users(course_id)

    # only users wíth roleid = STUDENT_ROLE_ID are real users 
    users_list = [item for item in users_and_teacher_list if any(d['roleid'] == roles_dict['STUDENT_ROLE_ID'] for d in item['roles'])]

    # users with roleid = TRAINER_ROLE_ID are trainers
    trainers_list = [item for item in users_and_teacher_list if any(d['roleid'] == roles_dict['TRAINER_ROLE_ID'] for d in item['roles'])]
 
    for user_dict in users_list:
        user, _ = EventMember.objects.filter(event__moodle_id=course_id).update_or_create(
            email=user_dict['email'],
            defaults={
                'event': event,
                'firstname': user_dict['firstname'],
                'lastname': user_dict['lastname'],
                'moodle_id': user_dict['id'],
                'enroled': True
            }
        )

        # payload : fill extra table with moodle users
        moodle_user, _ = MoodleUser.objects.update_or_create(
            email=user_dict['email'],
            defaults={
                'firstname': user_dict['firstname'],
                'lastname': user_dict['lastname'],
                'moodle_id': user_dict['id'],
            }
        )

        # in a second step update or create role assignments by use of the m2m through table

        # create necessary Roles if not existent
        # 1 = manager, 3 = teacher (Trainer), 5 = student (Teilnehmer)

        for v in roles_dict.values():
            role, _ = MemberRole.objects.get_or_create(roleid=v)

        for role in user_dict['roles']:
            print(f"Rolle: {role['roleid']}, usermoodleid: {user.moodle_id}")
            #myuser = EventMember.objects.get(moodle_id=user.moodle_id, event=event)
            print(user.id)
            role_obj = MemberRole.objects.get(roleid=role['roleid'])
            event_member_role, _ = EventMemberRole.objects.get_or_create(eventmember=user, memberrole=role_obj)

    # all users that are still in database associated to the course but removed in moodle are deleted
    # idea from: https://stackoverflow.com/questions/58412462/delete-multiple-django-objects-via-orm
    users_to_delete = EventMember.objects.filter(event=event, moodle_id__gt=0).exclude(moodle_id__in=[user_dict['id'] for user_dict in users_list])
    print(f"Event: {event.name}, users to delete: {users_to_delete}")
    users_to_delete.delete()

    # trainers
    # get or create trainer in terms of email 
    for trainer_dict in trainers_list:
        obj, created = EventSpeaker.objects.update_or_create(
            email=trainer_dict['email'],
            defaults={
                'first_name': trainer_dict['firstname'],
                'last_name': trainer_dict['lastname'],
            } 
        )
        # update EventSpeakerThrough table
        trainer, _ = EventSpeakerThrough.objects.get_or_create(event=event, eventspeaker=obj)
     

def get_user_by_email(email):
    fname = 'core_user_get_users_by_field'
    course_dict = {
        'field': 'email',
        'values[0]': email
    }
    user = call(fname, **course_dict)
    print(f"user: {user}")
    return user

#TODO: merge get_user_by_email and get_user_by_username to one function
def get_user_by_username(username):
    fname = 'core_user_get_users_by_field'
    course_dict = {
        'field': 'username',
        'values[0]': username
    }
    user = call(fname, **course_dict)
    print(f"user: {user}")
    return user

def enrol_user_to_course(email, courseid, new_user_password_flag, moodle_standard_password, roleid, firstname=None, lastname=None):
    #  check if user exists
    user = get_user_by_email(email)
    print(f"email trainer: {email}")
    
    if len(user) > 0:
        # user_id = user[0]['id']
        #print(f"user_id: {user_id}")
        fname = 'enrol_manual_enrol_users'
        course_dict = {
            'enrolments[0][roleid]': roleid,
            'enrolments[0][userid]': user[0]['id'],
            'enrolments[0][courseid]': courseid
        }
        call(fname, **course_dict)
    else:
        # create new user in moodle
        fname = 'core_user_create_users'

        # function for replacing umlaute
        def convert_umlaute(string_with_umlaute):
            umlaute_dict = {
                'ä': 'ae',
                'ü': 'ue',
                'ö': 'oe',
                'ß': 'ss'
            }
            for k in umlaute_dict.keys():
                string_with_umlaute = string_with_umlaute.replace(k, umlaute_dict[k])

            return string_with_umlaute

        # create unique username
        username_candidate = username_original = convert_umlaute(lastname.lower()) # standard username

        for i in itertools.count(1):
            # check if username_candidate in moodle exists
            user = get_user_by_username(username_candidate)
            if len(user) == 0:
                break
            username_candidate = '{}-{}'.format(username_original, i)

        username = username_candidate

        # if moodle_new_user_flag is set to True (default=False) a password is created an sent to new user
        if new_user_password_flag or email in test_user_list:
            createpassword = 1
        else:
            createpassword = 0

        course_dict = {
            'users[0][username]': username,
            'users[0][createpassword]': createpassword,
            'users[0][firstname]': firstname,
            'users[0][lastname]': lastname,
            'users[0][email]': email
        }

        if createpassword == 0:
            course_dict['users[0][password]'] = moodle_standard_password
            
        new_user = call(fname, **course_dict)
        user_id = new_user[0]['id']
        # update user in db with moodle_id
        EventMember.objects.filter(email=email).update(moodle_id=user_id)
        fname = 'enrol_manual_enrol_users'
        course_dict = {
            'enrolments[0][roleid]': roleid,
            'enrolments[0][userid]': user_id,
            'enrolments[0][courseid]': courseid
        }
        response = call(fname, **course_dict)
        print(response)
        return response


def unenrol_user_from_course(user, courseid):
    '''
    unenrol user from moodle course
    '''
    fname = 'enrol_manual_unenrol_users'
    course_dict = {
        'enrolments[0][userid]': user,
        'enrolments[0][courseid]': courseid,
    }
    call(fname, **course_dict)

def assign_roles_to_enroled_user(course_id, user_id, role_id_list):
    print(f"roles: {role_id_list}")
    for role_id in role_id_list:
        course_dict = {
            'enrolments[0][userid]': user_id,
            'enrolments[0][courseid]': course_id,
            'enrolments[0][roleid]': role_id,
        }
        fname = 'enrol_manual_enrol_users'
        response = call(fname, **course_dict)
        print(response)

def create_moodle_course(fullname, shortname, teaser, moodle_new_user_flag, moodle_standard_password, categoryid, speakers, first_day, last_day):
    '''
    creates Moodle Course with minimal necessary data
    '''
    #TODO: check if course already exists
    fname = 'core_course_create_courses'
    # combine date and time objects to datetime object
    tz = pytz.timezone('Europe/Berlin')
    startdatetime = datetime.datetime.combine(first_day.start_date, first_day.start_time)
    enddatetime = datetime.datetime.combine(last_day.start_date, last_day.end_time)
    # convert datetime objects to timestamp
    
    timestamp_start = int(startdatetime.timestamp())
    timestamp_end = int(enddatetime.timestamp())
    #timestamp_end = datetime.datetime.timestamp(enddatetime)
    course_dict = {
        'courses[0][fullname]': fullname,
        'courses[0][shortname]': shortname,
        'courses[0][summary]': teaser,
        'courses[0][categoryid]': categoryid,
        'courses[0][startdate]': timestamp_start,
        'courses[0][enddate]': timestamp_end,
    }
    print(course_dict)
    response = call(fname, **course_dict)
    #print(f"neuer kurs response: {response}")
    # falls Kurs angelegt wurde:
    if response[0].get('id'):
        print(f"neuer kurs response: {response[0].get('id')}")
        speaker = create_or_update_trainer(response[0].get('id'), moodle_new_user_flag, moodle_standard_password, speakers)

    return response

def delete_moodle_course(moodleid):
    '''
    deletes Moodle Course with given id
    '''
    print(f"course zu löschen: {moodleid}")
    fname = 'core_course_delete_courses'
    course_dict = {
        'courseids[0]': moodleid,
    }
    response = call(fname, **course_dict)
    return response

def create_or_update_trainer(courseid, moodle_new_user_flag, moodle_standard_password, speakers):
    '''
    wenn ein Kurs in Moodle angelegt wird und Trainer hat,
    muss gecheckt werden:
    - gibt es den Trainer bereits in Moodle (Abgleich per E-Mail)?
      => dann zuordnen
    - es gibt den Trainer noch nicht => anlegen und zuordnen
    Diese Unterscheidung macht die Funktion enrol_user_to_course
    '''
    for speaker in speakers:
        if speaker.email:
            enrol_user_to_course(speaker.email, courseid, moodle_new_user_flag, moodle_standard_password, roles_dict['TRAINER_ROLE_ID'], speaker.first_name, speaker.last_name)

      




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
        #print(id_list_of_moodle_courses)
        moodle_courses_in_db = Event.objects.filter(moodle_id__gt=0).values_list('moodle_id', flat=True)

        moodle_id_list_from_db = list(moodle_courses_in_db)
        #print(moodle_id_list_from_db)

        moodle_only_in_db_set = list(set(set(moodle_id_list_from_db) - set(id_list_of_moodle_courses)))
        #print(moodle_only_in_db_set)

        # delete all courses only in db
        Event.objects.filter(moodle_id__in=moodle_only_in_db_set).delete()

        for course in courses:
            #print(f"Kurs: {course['fullname']}")
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

            '''
            nur die Kurse aus den Bereichen in Planung(id = 3) und 
            Fortbildungen (id=4) werden gespeichert
            '''
            if course_cat_id == 3 or course_cat_id == 4:
                save_course_to_db(course_dict)

            #print(course_dict)
            #print(trainer_dict)
            
            
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