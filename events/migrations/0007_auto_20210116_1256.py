# Generated by Django 3.1.5 on 2021-01-16 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_auto_20210116_0713'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='emailtemplate',
            options={'verbose_name': 'Email-Vorlage', 'verbose_name_plural': 'Email-Vorlagen'},
        ),
        migrations.AddField(
            model_name='event',
            name='slug',
            field=models.SlugField(null=True),
        ),
    ]
