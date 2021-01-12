from .models import EventCategory

def category_renderer(request):
    return {
       'all_categories': EventCategory.objects.all(),
    }