# Generated by Django 3.2.15 on 2025-02-13 07:13

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0165_auto_20250110_2053'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='costs',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Kosten der Veranstaltung', max_digits=10, verbose_name='Kosten'),
        ),
        migrations.AlterField(
            model_name='eventcategory',
            name='belongs_to_all_events',
            field=models.BooleanField(default=True, verbose_name='gehört zu VFLL-Fortbildungen'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2025, 2, 13), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]
