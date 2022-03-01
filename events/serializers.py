from rest_framework import serializers
from datetime import datetime
from .models import Event, EventSpeaker


class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ("first_name", "last_name")


class EventSerializer(serializers.ModelSerializer):

    speaker = SpeakerSerializer(read_only=True, many=True)
    category_name = serializers.CharField(source="category.title")
    first_day = serializers.DateField(format="%d.%m.%Y")
    event_absolute_url = serializers.URLField(source="get_absolute_url", read_only=True)

    # ref: https://stackoverflow.com/questions/33016149/including-the-get-absolute-url-value-in-json-output

    class Meta:
        model = Event
        fields = (
            "id",
            "category_name",
            "name",
            "first_day",
            "event_absolute_url",
            "description",
            "speaker",
        )
