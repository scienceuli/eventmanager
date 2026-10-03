from celery.schedules import crontab
from celery import shared_task

# from celery.decorators import periodic_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task
def foo(x, y):
    return x * y
