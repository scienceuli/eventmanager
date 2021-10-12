# Generated by Django 3.1.5 on 2021-10-12 00:29

import ckeditor_uploader.fields
import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0086_auto_20210912_0752'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventsponsorthrough',
            options={'ordering': ['position'], 'verbose_name': 'Pat*in', 'verbose_name_plural': 'Pat*innen'},
        ),
        migrations.AlterField(
            model_name='event',
            name='prerequisites',
            field=ckeditor_uploader.fields.RichTextUploadingField(verbose_name='Voraussetzungen'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2021, 10, 12), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]