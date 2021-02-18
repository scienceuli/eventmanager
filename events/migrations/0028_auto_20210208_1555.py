# Generated by Django 3.1.5 on 2021-02-08 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0027_auto_20210204_0501'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventmember',
            name='check',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='eventmember',
            name='message',
            field=models.TextField(blank=True, verbose_name='Anmerkung'),
        ),
    ]