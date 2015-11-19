from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe

from is_core.main import UIRESTModelISCore
from is_core.generic_views.inlines.inline_objects_views import TabularInlineObjectsView

from reversion.models import Revision, Version

from .views import ReversionEditView, ReversionHistoryView


class DataRevisionIsCore(UIRESTModelISCore):
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
    form_readonly_fields = ('V', 'user', 'comment', 'serialized_data')

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
            from is_core.utils import get_obj_url

            obj = version.object
            obj_url = get_obj_url(self.request, obj)

            if (obj_url):
                return mark_safe('<a href="%s">%s</a>' % (obj_url, force_text(obj)))
            return obj

        def get_objects(self):
            return self.parent_instance.versions.all()


    form_inline_views = [VersionInlineFormView]


class ReversionUIRESTModelISCore(UIRESTModelISCore):
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
