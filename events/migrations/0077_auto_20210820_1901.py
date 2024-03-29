# Generated by Django 3.1.5 on 2021-08-20 19:01

import ckeditor.fields
import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0076_auto_20210729_1220'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='free_text_field_intro',
            field=ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Freitextfeld Intro'),
        ),
        migrations.AddField(
            model_name='eventmember',
            name='free_text_field',
            field=models.TextField(blank=True, verbose_name='Freitext'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2021, 8, 20), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
        migrations.AlterField(
            model_name='eventmember',
            name='vote_transfer_check',
            field=models.BooleanField(default=False, verbose_name='Check Stimmübertragung'),
        ),
    ]
