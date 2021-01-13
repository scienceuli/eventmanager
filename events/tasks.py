
from celery.schedules import crontab
from celery import shared_task 
# from celery.decorators import periodic_task
from celery.utils.log import get_task_logger

from events.api import call

logger = get_task_logger(__name__)


@shared_task
def get_courses_from_moodle():
    """
    Saves latest courses from Moodle
    """
    fname = 'core_course_get_courses'
    courses_list = call(fname)
    logger.info("Get courses from Moodle")
