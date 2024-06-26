# Generated by Django 3.2.9 on 2021-12-03 03:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0014_auto_20211203_0347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='task_interest',
            field=models.ManyToManyField(limit_choices_to=models.Q(('task__conference', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='evalbase.conference'))), related_name='iterested_orgs', to='evalbase.Task'),
        ),
    ]
