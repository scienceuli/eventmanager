# Generated by Django 3.1.5 on 2023-07-28 20:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0131_auto_20230728_1715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paylessaction',
            name='percents',
            field=models.SmallIntegerField(blank=True, default=0, verbose_name='Prozente'),
        ),
    ]
