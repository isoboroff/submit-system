# Generated by Django 3.0 on 2019-12-04 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0003_submitformfield_question_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='submitformfield',
            name='choices',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]