from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

from is_core.main import UIRestModelISCore
from is_core.generic_views.inlines.inline_objects_views import TabularInlineObjectsView

from reversion.models import Revision, Version, AuditLog

from .views import ReversionEditView, ReversionHistoryView


class DataRevisionISCore(UIRestModelISCore):
    abstract = True

    model = Revision
    list_display = ('created_at', 'user', 'comment')
    rest_list_fields = ('pk',)
    rest_list_obj_fields = ('pk',)
    menu_group = 'data-revision'

    form_fieldsets = (
        (None, {'fields': ('created_at', 'user', 'comment')}),
        (_('Versions'), {'inline_view': 'VersionInlineFormView'}),
    )
    form_readonly_fields = ('user', 'comment', 'serialized_data')

    def has_create_permission(self, request, obj=None):
        return False

    def has_update_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class VersionInlineFormView(TabularInlineObjectsView):
        model = Version
        fields = (
            ('type', _('type')),
            ('content_type', _('content type')),
            ('object', _('object')),
            ('data', _('data')),
        )

        def parse_object(self, obj):
            return {'type': obj.get_type_display(), 'object': self.get_object(obj), 'content_type': obj.content_type,
                    'data': ', '.join(('%s: %s' % (k, v if v != '' else '--') for k, v in obj.flat_field_dict.items()))}

        def get_object(self, version):
            from is_core.utils import render_model_object_with_link

            obj = version.object
            if obj:
                return render_model_object_with_link(self.request, obj)
            return obj

        def get_objects(self):
            return self.parent_instance.versions.all()

    form_inline_views = [VersionInlineFormView]


class ReversionUIRESTModelISCore(UIRestModelISCore):
    abstract = True

    def get_view_classes(self):
        view_classes = super(ReversionUIRESTModelISCore, self).get_view_classes()
        view_classes['history'] = (r'^/(?P<pk>\d+)/history/?$', ReversionHistoryView)
        view_classes['edit'] = (r'^/(?P<pk>\d+)/$', ReversionEditView)
        return view_classes

    def has_create_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class AuditLogUIRESTModelISCore(UIRestModelISCore):
    abstract = True
    model = AuditLog
    list_display = ('created_at', 'content_types', 'object_pks', 'short_comment')
    form_fields = ('created_at', 'related_objects_display', 'revisions_display', 'comment')
    menu_group = 'audit-log'

    def has_create_permission(self, *args, **kwargs):
        return False

    def has_update_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
