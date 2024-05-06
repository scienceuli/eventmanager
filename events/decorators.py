from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

# ref: https://dmitry-naumenko.medium.com/how-to-create-a-decorator-for-checking-groups-in-django-40a9df327c4b
# usage:
# @check_user_able_to_see_page("admin", "manager")
# def hidden_page(request):
#   ...


def check_user_able_to_see_page(*groups):

    def decorator(function):
        def wrapper(request, *args, **kwargs):
            if request.user.groups.filter(name__in=groups).exists():
                return function(request, *args, **kwargs)
            raise PermissionDenied

        return wrapper

    return decorator
