from rest_framework import serializers
from datetime import datetime
from .models import Event, EventSpeaker

class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ('first_name', 'last_name')

class EventSerializer(serializers.ModelSerializer):

    speaker = SpeakerSerializer(read_only=True, many=True)
    category_name = serializers.CharField(source='category.name')
    first_day = serializers.DateField(format="%d.%m.%Y")

    class Meta:
        model = Event
        fields = ('id','category_name', 'name', 'first_day', 'description', 'speaker',)