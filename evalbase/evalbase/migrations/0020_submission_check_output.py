# Generated by Django 4.1.4 on 2023-11-27 22:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0019_task_checker_file_alter_task_conference'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='check_output',
            field=models.TextField(blank=True),
        ),
    ]
