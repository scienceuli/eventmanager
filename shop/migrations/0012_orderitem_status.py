# Generated by Django 3.2.15 on 2024-02-01 18:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_order_mail_sent_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('r', 'registriert'), ('w', 'Warteliste'), ('s', 'storniert'), ('n', 'nicht erschienen'), ('u', 'unklar')], default='r', max_length=1),
        ),
    ]