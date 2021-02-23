from django.contrib import admin

from .models import Task, Project, Comment

class CommentInlineAdmin(admin.TabularInline):
    model = Comment
    fields = ['created_by', 'title', 'description']
    readonly_fields = ['created_by']
    extra = 1

    

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = ['title', 'description']
    list_display = ['title',  'task_type', 'severity', 'close_date', 'status']
    date_hierarchy = 'close_date'
    inlines = (CommentInlineAdmin,)
    fields = ['project', 'title', 'description', 'task_type', 'severity', 'close_date', 'status', 'created_by']
    readonly_fields = ['created_by']
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.created_by = request.user
            instance.save()
        formset.save_m2m()
    

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ['title', 'description']

