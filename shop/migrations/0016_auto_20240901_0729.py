# Generated by Django 3.2.15 on 2024-09-01 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0015_auto_20240709_1445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='replacement_date',
            field=models.CharField(blank=True, help_text='Zum Überschreiben des automatisch erzeugten Veranstaltungsdatums. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.', max_length=40, null=True, verbose_name='Ersatzangabe Event Datum'),
        ),
        migrations.AlterField(
            model_name='order',
            name='replacement_event',
            field=models.CharField(blank=True, help_text='Zum Überschreiben des automatisch erzeugten Veranstaltungstitels. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.', max_length=255, null=True, verbose_name='Ersatzangabe Event Name'),
        ),
        migrations.AlterField(
            model_name='order',
            name='use_replacements',
            field=models.BooleanField(default=False, help_text='Anklicken, um Ersatzangaben zu benutzen', verbose_name='Ersatzangaben benutzen'),
        ),
    ]
