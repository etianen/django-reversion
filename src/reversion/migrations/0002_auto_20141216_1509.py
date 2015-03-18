# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='revision',
            name='manager_slug',
            field=models.CharField(default='default', max_length=191, db_index=True),
        ),
    ]
