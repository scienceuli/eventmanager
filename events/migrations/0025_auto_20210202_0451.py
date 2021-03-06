# Generated by Django 3.1.5 on 2021-02-02 04:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0024_auto_20210131_0717'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventmember',
            name='memberships',
            field=models.CharField(blank=True, max_length=5, verbose_name='Mitgliedschaften'),
        ),
        migrations.AddField(
            model_name='eventmember',
            name='vfll',
            field=models.BooleanField(default=False, verbose_name='VFLL-Mitglied'),
        ),
    ]
