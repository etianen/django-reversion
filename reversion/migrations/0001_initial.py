# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Revision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('manager_slug', models.CharField(default='default', max_length=200, db_index=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='The date and time this revision was created.', verbose_name='date created', db_index=True)),
                ('comment', models.TextField(help_text='A text comment on this revision.', verbose_name='comment', blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, help_text='The user who created this revision.', null=True, verbose_name='user')),
            ],
            options={
                "ordering": ("-pk",)
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.TextField(help_text='Primary key of the model under version control.')),
                ('object_id_int', models.IntegerField(help_text="An indexed, integer version of the stored model's primary key, used for faster lookups.", null=True, db_index=True, blank=True)),
                ('format', models.CharField(help_text='The serialization format used by this model.', max_length=255)),
                ('serialized_data', models.TextField(help_text='The serialized form of this version of the model.')),
                ('object_repr', models.TextField(help_text='A string representation of the object.')),
                ('content_type', models.ForeignKey(help_text='Content type of the model under version control.', on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('revision', models.ForeignKey(help_text='The revision that contains this version.', on_delete=django.db.models.deletion.CASCADE, to='reversion.Revision')),
            ],
            options={
                "ordering": ("-pk",)
            },
            bases=(models.Model,),
        ),
    ]
