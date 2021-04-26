import requests
import json

from django.conf import settings

from .warnings import Warning
from .exception import MoodleException

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

def moodle_to_database():
    pass


