from django.contrib import admin

from .models import Task, Project

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = ['title', 'description']
    list_display = ['title',  'task_type', 'severity', 'close_date', 'status']
    date_hierarchy = 'close_date'
    fields = ['project', 'title', 'description', 'task_type', 'severity', 'close_date', 'status']

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)
    

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ['title', 'description']

