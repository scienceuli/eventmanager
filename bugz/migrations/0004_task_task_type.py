# Generated by Django 3.1.5 on 2021-02-22 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bugz', '0003_auto_20210222_2008'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='task_type',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Bug'), (2, 'Feature')], default=1, verbose_name='Typ'),
        ),
    ]
