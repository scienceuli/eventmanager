# Generated by Django 3.1.5 on 2021-03-19 17:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0037_auto_20210319_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='speaker',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='speaker_events', to='events.eventspeaker', verbose_name='Referent/-in'),
        ),
    ]
