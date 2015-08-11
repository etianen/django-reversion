from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from is_core.generic_views.inlines.inline_objects_views import TabularInlineObjectsView
from is_core.generic_views.mixins import TabsViewMixin
from is_core.generic_views.form_views import EditModelFormView, DetailModelFormView

from is_core.patterns import reverse_pattern


class ReversionTabsViewMixin(TabsViewMixin):

    def get_tabs(self):
        tabs = []
        tabs.append((_('Details'), reverse('IS:edit-%s' % self.core.menu_group, args=(self.kwargs.get('pk'),))))
        tabs.append((_('History'), reverse('IS:history-%s' % self.core.menu_group, args=(self.kwargs.get('pk'),))))
        return tabs


class ReversionBreadCrumbsTabsViewMixin(ReversionTabsViewMixin):

    def extra_parent_bread_crumbs_menu_items(self):
        from is_core.menu import LinkMenuItem

        return [
            LinkMenuItem(self.core.model._ui_meta.list_verbose_name % {
                    'verbose_name': self.core.model._meta.verbose_name,
                    'verbose_name_plural': self.core.model._meta.verbose_name_plural
                },
            reverse_pattern('list-%s' % self.core.menu_group).get_url_string(self.request), active=False),
            LinkMenuItem(self.core.model._ui_meta.edit_verbose_name % {
                    'verbose_name': self.core.model._meta.verbose_name,
                    'verbose_name_plural': self.core.model._meta.verbose_name_plural,
                    'obj': self.core.model.objects.get(pk=self.kwargs.get('pk'))
                },
            reverse_pattern('edit-%s' % self.core.menu_group).get_url_string(self.request,
                                                                             kwargs={'pk':self.kwargs.get('pk')}),
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
    inline_views = (ListVersionInlineView,)

    def get_title(self):
        return _('History of %s') % self.get_obj()

    def get_fieldsets(self):
        return (
            (_('History of %s') % self.get_obj(), {'inline_view': 'ListVersionInlineView'}),
        )
