# Generated by Django 3.1.5 on 2023-06-21 06:25

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0119_eventcollection_last_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='direct_payment',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2023, 6, 21), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]