# Generated by Django 3.2.15 on 2024-05-15 17:18

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0158_auto_20240506_2106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2024, 5, 15), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
        migrations.AlterField(
            model_name='eventmemberchangedate',
            name='action',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
