# Generated by Django 3.1.5 on 2022-07-14 13:51

import datetime
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0107_auto_20220705_0604'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventExternalSponsor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('name', models.CharField(blank=True, max_length=128, verbose_name='Vorname')),
                ('email', models.EmailField(blank=True, max_length=255, verbose_name='E-Mail')),
                ('phone', models.CharField(blank=True, max_length=64, verbose_name='Tel')),
                ('url', models.URLField(blank=True, verbose_name='Website')),
                ('image', models.ImageField(blank=True, upload_to='externalsponsors/')),
            ],
            options={
                'verbose_name': 'Sponsor',
                'verbose_name_plural': 'Sponsoren',
                'ordering': ('name',),
            },
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2022, 7, 14), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]