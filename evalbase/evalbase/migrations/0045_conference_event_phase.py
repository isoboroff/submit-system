# Generated by Django 5.1.2 on 2024-11-14 01:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evalbase", "0044_alter_statsfile_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="conference",
            name="event_phase",
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
