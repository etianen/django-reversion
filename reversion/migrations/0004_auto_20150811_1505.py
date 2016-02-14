# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0003_auto_20150805_2140'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='revision',
            options={'verbose_name': 'data revision', 'ordering': ('-created_at',), 'verbose_name_plural': 'data revisions'},
        ),
        migrations.AlterModelOptions(
            name='version',
            options={'verbose_name': 'data version', 'verbose_name_plural': 'data versions'},
        ),
        migrations.AlterField(
            model_name='revision',
            name='created_at',
            field=models.DateTimeField(verbose_name='created at', help_text='The date and time this revision was created.', db_index=True, auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='version',
            name='format',
            field=models.CharField(verbose_name='format', help_text='The serialization format used by this model.', max_length=255),
        ),
        migrations.AlterField(
            model_name='version',
            name='object_id',
            field=models.TextField(verbose_name='object id', help_text='Primary key of the model under version control.'),
        ),
        migrations.AlterField(
            model_name='version',
            name='object_id_int',
            field=models.IntegerField(verbose_name='object id int', help_text="An indexed, integer version of the stored model's primary key, used for faster lookups.", blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='version',
            name='object_repr',
            field=models.TextField(verbose_name='object representation', help_text='A string representation of the object.'),
        ),
        migrations.AlterField(
            model_name='version',
            name='revision',
            field=models.ForeignKey(verbose_name='revision', help_text='The revision that contains this version.', to='reversion.Revision', related_name='versions'),
        ),
        migrations.AlterField(
            model_name='version',
            name='serialized_data',
            field=models.TextField(verbose_name='serialized data', help_text='The serialized form of this version of the model.'),
        ),
        migrations.AlterField(
            model_name='version',
            name='type',
            field=models.PositiveIntegerField(verbose_name='version type', choices=[(1, 'Created'), (2, 'Changed'), (3, 'Deleted'), (4, 'Follow')]),
        ),
    ]
