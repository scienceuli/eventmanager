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
    url = serializers.HyperlinkedIdentityField(view_name='events:event-detail', read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'url', 'category_name', 'name', 'first_day', 'description', 'speaker',)