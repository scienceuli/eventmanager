# Generated by Django 3.2.15 on 2024-09-01 07:29

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0163_auto_20240808_1435'),
    ]

    operations = [
        migrations.CreateModel(
            name='VfllMemberEmail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.AlterField(
            model_name='event',
            name='registration_form',
            field=models.CharField(choices=[('s', 'Standard'), ('w', 'Willkommensveranstaltung'), ('m', 'MV/ZW'), ('f', 'Fachtagung 2022/MV'), ('f24', 'Fachtagung 2024/MV')], default='s', max_length=3, verbose_name='Anmeldeformular'),
        ),
        migrations.AlterField(
            model_name='eventhighlight',
            name='event',
            field=models.ForeignKey(limit_choices_to={'first_day__gte': datetime.date(2024, 9, 1), 'pub_status': 'PUB'}, on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event'),
        ),
    ]
