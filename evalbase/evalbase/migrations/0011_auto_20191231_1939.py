# Generated by Django 3.0 on 2019-12-31 19:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0010_auto_20191231_1937'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submitmeta',
            name='form',
        ),
        migrations.AddField(
            model_name='submitmeta',
            name='form_field',
            field=models.ForeignKey(default=7, on_delete=django.db.models.deletion.PROTECT, to='evalbase.SubmitFormField'),
            preserve_default=False,
        ),
    ]
