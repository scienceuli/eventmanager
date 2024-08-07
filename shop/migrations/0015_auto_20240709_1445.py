# Generated by Django 3.2.15 on 2024-07-09 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_order_storno'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='replacement_date',
            field=models.CharField(blank=True, max_length=40, null=True, verbose_name='Ersatzangabe Event Datum'),
        ),
        migrations.AddField(
            model_name='order',
            name='replacement_event',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Ersatzangabe Event Name'),
        ),
        migrations.AddField(
            model_name='order',
            name='use_replacements',
            field=models.BooleanField(default=False, verbose_name='Ersatzangaben benutzen'),
        ),
    ]
