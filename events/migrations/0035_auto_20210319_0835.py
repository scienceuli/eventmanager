# Generated by Django 3.1.5 on 2021-03-19 08:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0034_auto_20210319_0814'),
    ]

    operations = [
        migrations.RenameField(
            model_name='eventmember',
            old_name='role_id',
            new_name='roles',
        ),
    ]