# Generated by Django 5.0 on 2024-05-14 14:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

def migrate_task_forward(apps, schema_editor):
    Task = apps.get_model('evalbase', 'Task')
    Track = apps.get_model('evalbase', 'Track')

    for task in Task.objects.all():
        new_track = Track(
            shortname=task.shortname,
            longname=task.longname,
            conference=task.conference,
            url=task.url)
        new_track.save()

        new_track.coordinators.set(task.coordinators.all())
        new_track.save()

        task.track = new_track
        task.shortname = new_track.conference.shortname + '_' + task.shortname
        task.save()


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0027_task_url'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shortname', models.CharField(max_length=15)),
                ('longname', models.CharField(max_length=50)),
                ('url', models.URLField(blank=True)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='evalbase.conference')),
                ('coordinators', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='organization',
            name='track_interest',
            field=models.ManyToManyField(to='evalbase.track'),
        ),
        migrations.AddField(
            model_name='task',
            name='track',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='evalbase.track'),
        ),
        migrations.AlterField(
            model_name='task',
            name='shortname',
            field=models.CharField(max_length=25),
        ),

        migrations.RunPython(migrate_task_forward, None),
    ]
