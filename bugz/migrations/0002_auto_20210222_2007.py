# Generated by Django 3.1.5 on 2021-02-22 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bugz', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='close_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='erledigen bis'),
        ),
        migrations.AlterField(
            model_name='task',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Titel'),
        ),
    ]