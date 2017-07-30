from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.urlresolvers import reverse

from is_core.generic_views.inlines.inline_objects_views import TabularInlineObjectsView
from is_core.generic_views.mixins import TabsViewMixin
from is_core.generic_views.form_views import EditModelFormView, DetailModelFormView
from is_core.patterns import reverse_pattern

from reversion.models import Version


class VersionInlineFormView(TabularInlineObjectsView):
    model = Version
    fields = (
        ('type', _('type')),
        ('content_type', _('content type')),
        ('object', _('object')),
        ('data', _('data')),
    )

    def parse_object(self, obj):
        return {
            'type': obj.get_type_display(), 'object': self.get_object(obj), 'content_type': obj.content_type,
            'data': ', '.join(('{}: {}'.format(k, v if v != '' else '--') for k, v in obj.flat_field_dict.items()))
        }

    def get_object(self, version):
        from is_core.utils import render_model_object_with_link

        obj = version.object
        if obj:
            return render_model_object_with_link(self.request, obj)
        return obj

    def get_objects(self):
        return self.parent_instance.versions.all()


class ReversionTabsViewMixin(TabsViewMixin):

    def get_tabs(self):
        return (
            (ugettext('Details'), reverse('IS:edit-%s' % self.core.menu_group, args=(self.kwargs.get('pk'),))),
            (ugettext('History'), reverse('IS:history-%s' % self.core.menu_group, args=(self.kwargs.get('pk'),))),
        )


class ReversionBreadCrumbsTabsViewMixin(ReversionTabsViewMixin):

    def extra_parent_bread_crumbs_menu_items(self):
        from is_core.menu import LinkMenuItem

        return [
            LinkMenuItem(self.core.model._ui_meta.list_verbose_name % {
                'verbose_name': self.core.model._meta.verbose_name,
                'verbose_name_plural': self.core.model._meta.verbose_name_plural
            }, reverse_pattern('list-%s' % self.core.menu_group).get_url_string(self.request), active=False),
            LinkMenuItem(self.core.model._ui_meta.edit_verbose_name % {
                'verbose_name': self.core.model._meta.verbose_name,
                'verbose_name_plural': self.core.model._meta.verbose_name_plural,
                'obj': self.core.model.objects.get(pk=self.kwargs.get('pk'))
            }, reverse_pattern('edit-%s' % self.core.menu_group).get_url_string(self.request,
                                                                                kwargs={'pk': self.kwargs.get('pk')}),
                         active=False)
        ]

    def bread_crumbs_menu_items(self):
        from is_core.menu import LinkMenuItem

        return self.extra_parent_bread_crumbs_menu_items() + [
            LinkMenuItem(self.get_title(), self.request.path, active=True)
        ]


class ReversionEditView(ReversionTabsViewMixin, EditModelFormView):
    pass


class ListVersionInlineView(TabularInlineObjectsView):

    def get_fields(self):
        if self.fields:
            return list(self.fields)
        else:
            fields = [('reversion_editor', _('user'))]
            for model_field in self.parent_instance._meta.fields:
                fields.append((model_field.name, model_field.verbose_name))

            return fields

    def get_objects(self):
        return self.parent_instance.reversion_versions.all()


class ReversionHistoryView(ReversionBreadCrumbsTabsViewMixin, DetailModelFormView):

    def get_title(self):
        return ugettext('History of %s') % self.get_obj()

    def get_fieldsets(self):
        return (
            (ugettext('History of %s') % self.get_obj(), {'inline_view': ListVersionInlineView}),
        )
