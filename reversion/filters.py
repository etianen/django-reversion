from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext

try:
    from is_core.filters.default_filters import DefaultFilter
    from is_core.filters.exceptions import FilterException
except ImportError:
    DefaultFilter = object
    FilterException = object


class RelatedObjectsFilter(DefaultFilter):
    widget = forms.TextInput()

    def get_filter_term(self, request):
        self._check_suffix()

        if '|' not in self.value:
            term = {
                'versions__object_id': self.value
            }
        else:
            content_type, object_id = self.value.split('|', 1)
            term = {
                'versions__object_id': object_id,
                'versions__content_type': content_type
            }
        return {''.join((self.get_filter_prefix(), key)): val for key, val in term.items()}


class VersionIDFilter(DefaultFilter):
    widget = forms.TextInput()

    def get_filter_term(self, request):
        self._check_suffix()
        return {''.join((self.get_filter_prefix(), 'versions__object_id')): self.value}


class VersionContextTypeFilter(DefaultFilter):
    ALL_LABEL = '--------'
    ALL_SLUG = '__all__'

    def get_widget(self, request):
        from reversion.models import AuditLog

        if self.widget:
            return self.widget

        formfield = forms.ModelChoiceField(queryset=ContentType.objects.filter(
            pk__in=AuditLog.objects.order_by('versions__content_type').values('versions__content_type').distinct()))
        formfield.choices = list(formfield.choices)
        if not formfield.choices[0][0]:
            del formfield.choices[0]
        formfield.choices.insert(0, (self.ALL_SLUG, self.ALL_LABEL))
        return formfield.widget

    def get_filter_term(self, request):
        suffix = self._check_suffix()
        if not suffix:
            if self.value == self.ALL_SLUG:
                return {}
        return {''.join((self.get_filter_prefix(), 'versions__content_type')): self.value}
