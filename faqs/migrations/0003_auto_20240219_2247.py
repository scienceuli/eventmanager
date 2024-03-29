# Generated by Django 3.2.15 on 2024-02-19 22:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faqs', '0002_question_position'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='position',
            field=models.PositiveSmallIntegerField(help_text='Reihenfolge der Programme in der Anzeige', null=True, verbose_name='Reihenfolge'),
        ),
        migrations.AlterField(
            model_name='question',
            name='question',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='question',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
    ]
