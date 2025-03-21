# Generated by Django 5.0 on 2024-08-26 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evalbase", "0038_alter_submitformfield_choices_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submitformfield",
            name="choices",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="submitformfield",
            name="help_text",
            field=models.CharField(blank=True, default="", max_length=1000),
        ),
        migrations.AlterField(
            model_name="submitformfield",
            name="question",
            field=models.CharField(max_length=1000),
        ),
    ]
