# Generated by Django 3.1.5 on 2021-06-07 12:38

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0065_auto_20210522_0259'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventHighlight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='angelegt am')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='geändert am')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='highlight', to='events.event')),
            ],
        ),
        migrations.AddConstraint(
            model_name='eventhighlight',
            constraint=models.CheckConstraint(check=models.Q(id=1), name='events_eventhighlight_single_instance'),
        ),
    ]
