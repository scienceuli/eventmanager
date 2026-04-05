from django.contrib import messages

def add_success(request, message, fail_silently=True):
    """Add a success message to the Django messages framework."""
    messages.success(request, message, fail_silently=fail_silently)

def add_error(request, message, fail_silently=True):
    """Add an error message to the Django messages framework."""
    messages.error(request, message, fail_silently=fail_silently)
