# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


def get_user_pk_field_fully_qualified_name():
    pk_field = User._meta.pk
    module = pk_field.__class__.__module__
    if module is None:
        return pk_field.__class__.__name__
    return module + '.' + pk_field.__class__.__name__


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding model 'Revision'
        db.create_table('reversion_revision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('reversion', ['Revision'])

        # Adding model 'Version'
        db.create_table('reversion_version', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reversion.Revision'])),
            ('object_id', self.gf('django.db.models.fields.TextField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('format', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('serialized_data', self.gf('django.db.models.fields.TextField')()),
            ('object_repr', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('reversion', ['Version'])

    def backwards(self, orm):
        # Deleting model 'Revision'
        db.delete_table('reversion_revision')

        # Deleting model 'Version'
        db.delete_table('reversion_version')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [],
                            {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')",
                     'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': (
                'django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__, "db_table": "'%s'" % User._meta.db_table},
            User._meta.pk.attname: (
                get_user_pk_field_fully_qualified_name(), [],
                {'primary_key': 'True',
                'db_column': "'%s'" % User._meta.pk.column}
            ),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)",
                     'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'reversion.revision': {
            'Meta': {'object_name': 'Revision'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [],
                     {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True',
                      'blank': 'True'})
        },
        'reversion.version': {
            'Meta': {'object_name': 'Version'},
            'content_type': (
                'django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.TextField', [], {}),
            'object_repr': ('django.db.models.fields.TextField', [], {}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['reversion.Revision']"}),
            'serialized_data': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['reversion']
