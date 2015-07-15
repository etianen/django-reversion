# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import test_reversion.models


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0002_auto_20141216_1509'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='InlineTestChildGenericModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.IntegerField(db_index=True)),
                ('name', models.CharField(max_length=100)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='InlineTestChildModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='InlineTestParentModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='InlineTestUnrelatedChildModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='InlineTestUnrelatedParentModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='ParentTestAdminModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('parent_name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ReversionTestModel1',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ReversionTestModel2',
            fields=[
                ('name', models.CharField(max_length=100)),
                ('id', models.CharField(serialize=False, max_length=100, default=test_reversion.models.get_str_pk, primary_key=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ReversionTestModel3',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RevisionMeta',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('age', models.IntegerField()),
                ('revision', models.OneToOneField(to='reversion.Revision')),
            ],
        ),
        migrations.CreateModel(
            name='TestFollowModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ChildTestAdminModel',
            fields=[
                ('parenttestadminmodel_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, to='test_reversion.ParentTestAdminModel', parent_link=True)),
                ('child_name', models.CharField(max_length=200)),
            ],
            bases=('test_reversion.parenttestadminmodel',),
        ),
        migrations.CreateModel(
            name='ReversionTestModel1Child',
            fields=[
                ('reversiontestmodel1_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, to='test_reversion.ReversionTestModel1', parent_link=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('test_reversion.reversiontestmodel1',),
        ),
        migrations.AddField(
            model_name='testfollowmodel',
            name='test_model_1',
            field=models.ForeignKey(to='test_reversion.ReversionTestModel1'),
        ),
        migrations.AddField(
            model_name='testfollowmodel',
            name='test_model_2s',
            field=models.ManyToManyField(to='test_reversion.ReversionTestModel2'),
        ),
        migrations.AddField(
            model_name='inlinetestunrelatedchildmodel',
            name='parent',
            field=models.ForeignKey(to='test_reversion.InlineTestUnrelatedParentModel'),
        ),
        migrations.AddField(
            model_name='inlinetestchildmodel',
            name='parent',
            field=models.ForeignKey(to='test_reversion.InlineTestParentModel', related_name='children'),
        ),
        migrations.CreateModel(
            name='ReversionTestModel1Proxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('test_reversion.reversiontestmodel1',),
        ),
    ]
