# Generated by Django 3.0 on 2019-12-31 20:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evalbase', '0011_auto_20191231_1939'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agreement',
            name='signed_by',
        ),
        migrations.AddField(
            model_name='signature',
            name='agreement',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='evalbase.Agreement'),
            preserve_default=False,
        ),
    ]