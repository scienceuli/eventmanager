# Generated by Django 3.1.5 on 2021-07-20 21:30

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0071_auto_20210709_0637'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='events.eventcategory', verbose_name='Kategorie'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2021, 7, 20), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]
