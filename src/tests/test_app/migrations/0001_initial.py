# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import test_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('reversion', '0002_auto_20141216_1509'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InlineTestChildGenericModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.IntegerField(db_index=True)),
                ('name', models.CharField(max_length=100)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InlineTestChildModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InlineTestParentModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InlineTestUnrelatedChildModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InlineTestUnrelatedParentModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ParentTestAdminModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('parent_name', models.CharField(max_length=200)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ChildTestAdminModel',
            fields=[
                ('parenttestadminmodel_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, to='test_app.ParentTestAdminModel', auto_created=True, serialize=False, primary_key=True)),
                ('child_name', models.CharField(max_length=200)),
            ],
            options={
            },
            bases=('test_app.parenttestadminmodel',),
        ),
        migrations.CreateModel(
            name='ReversionTestModel1',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReversionTestModel1Child',
            fields=[
                ('reversiontestmodel1_ptr', models.OneToOneField(parent_link=True, to='test_app.ReversionTestModel1', auto_created=True, serialize=False, primary_key=True, on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=('test_app.reversiontestmodel1',),
        ),
        migrations.CreateModel(
            name='ReversionTestModel2',
            fields=[
                ('name', models.CharField(max_length=100)),
                ('id', models.CharField(serialize=False, primary_key=True, default=test_app.models.get_str_pk, max_length=100)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReversionTestModel3',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RevisionMeta',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('age', models.IntegerField()),
                ('revision', models.OneToOneField(to='reversion.Revision', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestFollowModel',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('test_model_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_app.ReversionTestModel1')),
                ('test_model_2s', models.ManyToManyField(to='test_app.ReversionTestModel2')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='inlinetestunrelatedchildmodel',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_app.InlineTestUnrelatedParentModel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='inlinetestchildmodel',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_app.InlineTestParentModel', related_name='children'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='ReversionTestModel1Proxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('test_app.reversiontestmodel1',),
        ),
    ]
