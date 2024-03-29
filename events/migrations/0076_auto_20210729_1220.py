# Generated by Django 3.1.5 on 2021-07-29 12:20

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0075_auto_20210727_1142'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventmember',
            name='mail_to_member',
            field=models.BooleanField(default=False, verbose_name='m > member'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2021, 7, 29), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
        migrations.AlterField(
            model_name='eventmember',
            name='takes_part',
            field=models.BooleanField(default=False, verbose_name='Teilnahme'),
        ),
    ]
