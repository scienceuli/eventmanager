# Generated by Django 3.1.5 on 2021-01-14 22:17

import ckeditor.fields
import ckeditor_uploader.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', ckeditor_uploader.fields.RichTextUploadingField(verbose_name='Teaser')),
                ('duration', models.CharField(blank=True, max_length=255, null=True, verbose_name='Dauer')),
                ('target_group', models.CharField(max_length=255, verbose_name='Zielgruppe')),
                ('prerequisites', models.CharField(max_length=255, verbose_name='Voraussetzungen')),
                ('objectives', ckeditor_uploader.fields.RichTextUploadingField(verbose_name='Lernziele')),
                ('methods', models.CharField(blank=True, max_length=255, null=True, verbose_name='Methoden')),
                ('scheduled_status', models.CharField(choices=[('yet to scheduled', 'noch offen'), ('scheduled', 'terminiert')], max_length=25)),
                ('fees', ckeditor.fields.RichTextField(verbose_name='Gebühren')),
                ('catering', ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Verpflegung')),
                ('lodging', ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Übernachtung')),
                ('total_costs', ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Gesamtkosten')),
                ('registration', ckeditor.fields.RichTextField(verbose_name='Anmeldung')),
                ('notes', ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Hinweise')),
                ('start_date', models.DateTimeField(verbose_name='Beginn')),
                ('end_date', models.DateTimeField(verbose_name='Ende')),
                ('open_date', models.DateTimeField(blank=True, null=True, verbose_name='Anmeldefrist Beginn')),
                ('close_date', models.DateTimeField(blank=True, null=True, verbose_name='Anmeldefrist Ende')),
                ('maximum_attende', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('active', 'aktiv'), ('deleted', 'verschoben'), ('cancel', 'abgesagt')], max_length=10)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventFormat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('address_line', models.CharField(blank=True, max_length=255, null=True, verbose_name='Zusatz')),
                ('street', models.CharField(blank=True, max_length=55, null=True, verbose_name='Straße')),
                ('city', models.CharField(blank=True, max_length=255, null=True, verbose_name='Stadt')),
                ('state', models.CharField(blank=True, max_length=255, null=True, verbose_name='Bundesland')),
                ('postcode', models.CharField(blank=True, max_length=64, null=True, verbose_name='PLZ')),
                ('title', models.CharField(max_length=128)),
                ('url', models.URLField(blank=True, verbose_name='Veranstaltungsort Website')),
            ],
            options={
                'verbose_name': 'Veranstaltungsort',
                'verbose_name_plural': 'Veranstaltungsorte',
            },
        ),
        migrations.CreateModel(
            name='EventSpeaker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('first_name', models.CharField(max_length=128)),
                ('last_name', models.CharField(max_length=128)),
                ('email', models.EmailField(max_length=255)),
                ('phone', models.CharField(blank=True, max_length=64)),
                ('bio', models.TextField(blank=True)),
                ('url', models.URLField(blank=True)),
                ('social_url', models.URLField(blank=True)),
                ('image', models.ImageField(blank=True, upload_to='speaker/')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('image', models.ImageField(upload_to='event_image/')),
                ('event', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='events.event')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventAgenda',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('session_name', models.CharField(max_length=120, verbose_name='Programmteil')),
                ('speaker_name', models.CharField(blank=True, max_length=120, null=True)),
                ('start_time', models.TimeField(blank=True, null=True, verbose_name='Beginn')),
                ('end_time', models.TimeField(blank=True, null=True, verbose_name='Ende')),
                ('venue_name', models.CharField(max_length=255, verbose_name='wo')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.event')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='event',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.eventcategory'),
        ),
        migrations.AddField(
            model_name='event',
            name='eventformat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.eventformat'),
        ),
        migrations.AddField(
            model_name='event',
            name='location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='location_events', to='events.eventlocation'),
        ),
        migrations.AddField(
            model_name='event',
            name='speaker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='speaker_events', to='events.eventspeaker', verbose_name='Referent/-in'),
        ),
    ]
