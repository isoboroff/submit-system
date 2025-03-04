# Generated by Django 5.1.2 on 2025-02-18 05:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evalbase", "0050_orgconfthroughmodel_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="conference",
            field=models.ManyToManyField(
                related_name="participants", to="evalbase.conference"
            ),
        ),
    ]
