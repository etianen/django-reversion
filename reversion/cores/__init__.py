from django.utils.translation import ugettext_lazy as _

from is_core.main import UIRESTModelISCore

from reversion.models import Revision, AuditLog

from .views import ReversionEditView, ReversionHistoryView, VersionInlineFormView


class DataRevisionISCore(UIRESTModelISCore):
    abstract = True

    model = Revision
    list_display = ('created_at', 'user', 'comment')
    rest_list_fields = ('pk',)
    rest_list_obj_fields = ('pk',)
    menu_group = 'data-revision'

    form_fieldsets = (
        (None, {'fields': ('created_at', 'user', 'comment')}),
        (_('Versions'), {'inline_view': VersionInlineFormView}),
    )
    form_readonly_fields = ('user', 'comment', 'serialized_data')

    create_permission = False
    delete_permission = False
    update_permission = False


class ReversionUIRESTModelISCore(UIRESTModelISCore):
    abstract = True
    create_permission = False
    delete_permission = False

    def get_view_classes(self):
        view_classes = super(ReversionUIRESTModelISCore, self).get_view_classes()
        view_classes['history'] = (r'^/(?P<pk>\d+)/history/?$', ReversionHistoryView)
        view_classes['edit'] = (r'^/(?P<pk>\d+)/$', ReversionEditView)
        return view_classes


class AuditLogUIRESTModelISCore(UIRESTModelISCore):
    abstract = True
    model = AuditLog
    list_display = ('created_at', 'content_types', 'object_pks', 'short_comment', 'priority', 'slug')
    form_fields = ('created_at', 'comment', 'priority', 'slug', 'related_objects_display', 'revisions_display')
    menu_group = 'audit-log'
    create_permission = False
    delete_permission = False
    update_permission = False
