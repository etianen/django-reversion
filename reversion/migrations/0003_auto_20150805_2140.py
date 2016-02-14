# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0002_auto_20141216_1509'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='revision',
            options={'ordering': ('created_at',)},
        ),
        migrations.RenameField(
            model_name='revision',
            old_name='date_created',
            new_name='created_at',
        ),
        migrations.AddField(
            model_name='version',
            name='type',
            field=models.PositiveIntegerField(default=2, choices=[(1, 'Created'), (2, 'Changed'), (3, 'Deleted')]),
            preserve_default=False,
        ),
    ]
