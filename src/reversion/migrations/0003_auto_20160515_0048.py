# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-15 00:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0002_auto_20141216_1509'),
    ]

    operations = [
        migrations.AlterField(
            model_name='version',
            name='content_type',
            field=models.ForeignKey(db_index=False, help_text='Content type of the model under version control.', on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='version',
            name='object_id',
            field=models.CharField(help_text='Primary key of the model under version control.', max_length=191),
        ),
        migrations.RemoveField(
            model_name='version',
            name='object_id_int',
        ),
        migrations.AlterIndexTogether(
            name='version',
            index_together=set([('content_type', 'object_id')]),
        ),
    ]
