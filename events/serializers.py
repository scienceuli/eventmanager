from rest_framework import serializers
from datetime import datetime
from .models import Event, EventSpeaker

class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ('first_name', 'last_name')


class EventSerializer(serializers.HyperlinkedModelSerializer):

    speaker = SpeakerSerializer(read_only=True, many=True)
    category_name = serializers.CharField(source='category.name')
    first_day = serializers.DateField(format="%d.%m.%Y")
    web_url = serializers.SerializerMethodField()

    def get_web_url(self, obj):
        obj_url = obj.get_absolute_url()
        return self.context["request"].build_absolute_uri(obj_url)

    class Meta:
        model = Event
        fields = ('id', 'url','category_name', 'name', 'first_day', 'web_url', 'description', 'speaker',)