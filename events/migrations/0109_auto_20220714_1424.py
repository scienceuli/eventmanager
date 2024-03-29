# Generated by Django 3.1.5 on 2022-07-14 14:24

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0108_auto_20220714_1351'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventexternalsponsor',
            name='text',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='EventExternalSponsorThrough',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('position', models.PositiveSmallIntegerField(default=1)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.event', verbose_name='Veranstaltung')),
                ('eventexternalsponsor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.eventexternalsponsor', verbose_name='Sponsor')),
            ],
            options={
                'verbose_name': 'Sponsor',
                'verbose_name_plural': 'Sponsoren',
                'ordering': ['position'],
            },
        ),
        migrations.AddField(
            model_name='event',
            name='externalsponsors',
            field=models.ManyToManyField(through='events.EventExternalSponsorThrough', to='events.EventExternalSponsor', verbose_name='Sponsor'),
        ),
    ]
