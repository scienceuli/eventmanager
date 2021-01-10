from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField


class EventCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('event-category-list')

class Event(models.Model):
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    uid = models.PositiveIntegerField(unique=True)
    description = RichTextUploadingField()
    select_scheduled_status = (
        ('yet to scheduled', 'noch offen'),
        ('scheduled', 'terminiert')
    )
    scheduled_status = models.CharField(max_length=25, choices=select_scheduled_status)
    venue = models.CharField(verbose_name="Ort", max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    maximum_attende = models.PositiveIntegerField()
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('active', 'aktiv'),
        ('deleted', 'verschoben'),
        ('cancel', 'abgesagt'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('event-list')
    
    def created_updated(model, request):
        obj = model.objects.latest('pk')
        if obj.created_by is None:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

class EventImage(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='event_image/')