# Generated by Django 3.1.5 on 2021-05-06 13:13

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0058_auto_20210427_0508'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventagenda',
            name='description',
            field=ckeditor.fields.RichTextField(blank=True, verbose_name='Programm'),
        ),
    ]
