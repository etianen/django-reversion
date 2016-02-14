# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ReversionTestModel1'
        db.create_table(u'test_reversion_reversiontestmodel1', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'test_reversion', ['ReversionTestModel1'])

        # Adding model 'ReversionTestModel1Child'
        db.create_table(u'test_reversion_reversiontestmodel1child', (
            (u'reversiontestmodel1_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['test_reversion.ReversionTestModel1'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'test_reversion', ['ReversionTestModel1Child'])

        # Adding model 'ReversionTestModel2'
        db.create_table(u'test_reversion_reversiontestmodel2', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('id', self.gf('django.db.models.fields.CharField')(default=u'1', max_length=100, primary_key=True)),
        ))
        db.send_create_signal(u'test_reversion', ['ReversionTestModel2'])

        # Adding model 'ReversionTestModel3'
        db.create_table(u'test_reversion_reversiontestmodel3', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'test_reversion', ['ReversionTestModel3'])

        # Adding model 'TestFollowModel'
        db.create_table(u'test_reversion_testfollowmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('test_model_1', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['test_reversion.ReversionTestModel1'])),
        ))
        db.send_create_signal(u'test_reversion', ['TestFollowModel'])

        # Adding M2M table for field test_model_2s on 'TestFollowModel'
        m2m_table_name = db.shorten_name(u'test_reversion_testfollowmodel_test_model_2s')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('testfollowmodel', models.ForeignKey(orm[u'test_reversion.testfollowmodel'], null=False)),
            ('reversiontestmodel2', models.ForeignKey(orm[u'test_reversion.reversiontestmodel2'], null=False))
        ))
        db.create_unique(m2m_table_name, ['testfollowmodel_id', 'reversiontestmodel2_id'])

        # Adding model 'RevisionMeta'
        db.create_table(u'test_reversion_revisionmeta', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('revision', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['reversion.Revision'], unique=True)),
            ('age', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'test_reversion', ['RevisionMeta'])

        # Adding model 'ParentTestAdminModel'
        db.create_table(u'test_reversion_parenttestadminmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal(u'test_reversion', ['ParentTestAdminModel'])

        # Adding model 'ChildTestAdminModel'
        db.create_table(u'test_reversion_childtestadminmodel', (
            (u'parenttestadminmodel_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['test_reversion.ParentTestAdminModel'], unique=True, primary_key=True)),
            ('child_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal(u'test_reversion', ['ChildTestAdminModel'])

        # Adding model 'InlineTestChildGenericModel'
        db.create_table(u'test_reversion_inlinetestchildgenericmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'test_reversion', ['InlineTestChildGenericModel'])

        # Adding model 'InlineTestParentModel'
        db.create_table(u'test_reversion_inlinetestparentmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'test_reversion', ['InlineTestParentModel'])

        # Adding model 'InlineTestChildModel'
        db.create_table(u'test_reversion_inlinetestchildmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='children', to=orm['test_reversion.InlineTestParentModel'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'test_reversion', ['InlineTestChildModel'])

        # Adding model 'InlineTestUnrelatedParentModel'
        db.create_table(u'test_reversion_inlinetestunrelatedparentmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'test_reversion', ['InlineTestUnrelatedParentModel'])

        # Adding model 'InlineTestUnrelatedChildModel'
        db.create_table(u'test_reversion_inlinetestunrelatedchildmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['test_reversion.InlineTestUnrelatedParentModel'])),
        ))
        db.send_create_signal(u'test_reversion', ['InlineTestUnrelatedChildModel'])


    def backwards(self, orm):
        # Deleting model 'ReversionTestModel1'
        db.delete_table(u'test_reversion_reversiontestmodel1')

        # Deleting model 'ReversionTestModel1Child'
        db.delete_table(u'test_reversion_reversiontestmodel1child')

        # Deleting model 'ReversionTestModel2'
        db.delete_table(u'test_reversion_reversiontestmodel2')

        # Deleting model 'ReversionTestModel3'
        db.delete_table(u'test_reversion_reversiontestmodel3')

        # Deleting model 'TestFollowModel'
        db.delete_table(u'test_reversion_testfollowmodel')

        # Removing M2M table for field test_model_2s on 'TestFollowModel'
        db.delete_table(db.shorten_name(u'test_reversion_testfollowmodel_test_model_2s'))

        # Deleting model 'RevisionMeta'
        db.delete_table(u'test_reversion_revisionmeta')

        # Deleting model 'ParentTestAdminModel'
        db.delete_table(u'test_reversion_parenttestadminmodel')

        # Deleting model 'ChildTestAdminModel'
        db.delete_table(u'test_reversion_childtestadminmodel')

        # Deleting model 'InlineTestChildGenericModel'
        db.delete_table(u'test_reversion_inlinetestchildgenericmodel')

        # Deleting model 'InlineTestParentModel'
        db.delete_table(u'test_reversion_inlinetestparentmodel')

        # Deleting model 'InlineTestChildModel'
        db.delete_table(u'test_reversion_inlinetestchildmodel')

        # Deleting model 'InlineTestUnrelatedParentModel'
        db.delete_table(u'test_reversion_inlinetestunrelatedparentmodel')

        # Deleting model 'InlineTestUnrelatedChildModel'
        db.delete_table(u'test_reversion_inlinetestunrelatedchildmodel')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'reversion.revision': {
            'Meta': {'ordering': "(u'-created_at',)", 'object_name': 'Revision'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager_slug': ('django.db.models.fields.CharField', [], {'default': "u'default'", 'max_length': '191', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        u'test_reversion.childtestadminmodel': {
            'Meta': {'object_name': 'ChildTestAdminModel', '_ormbases': [u'test_reversion.ParentTestAdminModel']},
            'child_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'parenttestadminmodel_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['test_reversion.ParentTestAdminModel']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'test_reversion.inlinetestchildgenericmodel': {
            'Meta': {'object_name': 'InlineTestChildGenericModel'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'test_reversion.inlinetestchildmodel': {
            'Meta': {'object_name': 'InlineTestChildModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'to': u"orm['test_reversion.InlineTestParentModel']"})
        },
        u'test_reversion.inlinetestparentmodel': {
            'Meta': {'object_name': 'InlineTestParentModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'test_reversion.inlinetestunrelatedchildmodel': {
            'Meta': {'object_name': 'InlineTestUnrelatedChildModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['test_reversion.InlineTestUnrelatedParentModel']"})
        },
        u'test_reversion.inlinetestunrelatedparentmodel': {
            'Meta': {'object_name': 'InlineTestUnrelatedParentModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'test_reversion.parenttestadminmodel': {
            'Meta': {'object_name': 'ParentTestAdminModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'test_reversion.reversiontestmodel1': {
            'Meta': {'object_name': 'ReversionTestModel1'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'test_reversion.reversiontestmodel1child': {
            'Meta': {'object_name': 'ReversionTestModel1Child', '_ormbases': [u'test_reversion.ReversionTestModel1']},
            u'reversiontestmodel1_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['test_reversion.ReversionTestModel1']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'test_reversion.reversiontestmodel2': {
            'Meta': {'object_name': 'ReversionTestModel2'},
            'id': ('django.db.models.fields.CharField', [], {'default': "u'2'", 'max_length': '100', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'test_reversion.reversiontestmodel3': {
            'Meta': {'object_name': 'ReversionTestModel3'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'test_reversion.revisionmeta': {
            'Meta': {'object_name': 'RevisionMeta'},
            'age': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['reversion.Revision']", 'unique': 'True'})
        },
        u'test_reversion.testfollowmodel': {
            'Meta': {'object_name': 'TestFollowModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'test_model_1': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['test_reversion.ReversionTestModel1']"}),
            'test_model_2s': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['test_reversion.ReversionTestModel2']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['test_reversion']