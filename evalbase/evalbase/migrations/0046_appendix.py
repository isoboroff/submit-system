# Generated by Django 5.1.2 on 2024-11-14 16:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evalbase", "0045_conference_event_phase"),
    ]

    operations = [
        migrations.CreateModel(
            name="Appendix",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=40)),
                ("measure_name_field", models.IntegerField()),
                ("topic_field", models.IntegerField()),
                ("score_field", models.IntegerField()),
                ("measures", models.JSONField(max_length=1024)),
                ("sort_column", models.CharField(max_length=20)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="evalbase.task"
                    ),
                ),
            ],
        ),
    ]
