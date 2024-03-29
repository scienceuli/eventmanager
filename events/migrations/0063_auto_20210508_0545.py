# Generated by Django 3.1.5 on 2021-05-08 05:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0062_auto_20210506_1943'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventspeaker',
            options={'ordering': ('last_name',), 'verbose_name': 'Dozent*in', 'verbose_name_plural': 'Dozent*innen'},
        ),
        migrations.AlterModelOptions(
            name='eventspeakerthrough',
            options={'verbose_name': 'Dozent*in', 'verbose_name_plural': 'Dozent*innen'},
        ),
        migrations.AddField(
            model_name='eventcategory',
            name='title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='speaker',
            field=models.ManyToManyField(through='events.EventSpeakerThrough', to='events.EventSpeaker', verbose_name='Dozent*innen'),
        ),
        migrations.AlterField(
            model_name='eventspeakerthrough',
            name='eventspeaker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.eventspeaker', verbose_name='Dozent*in'),
        ),
    ]
