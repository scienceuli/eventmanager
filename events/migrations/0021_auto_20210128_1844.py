# Generated by Django 3.1.5 on 2021-01-28 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0020_auto_20210124_0643'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EventMember',
            new_name='EventMemberAnonymous',
        ),
        migrations.AlterField(
            model_name='event',
            name='students_number',
            field=models.PositiveSmallIntegerField(default=0, editable=False),
        ),
    ]
