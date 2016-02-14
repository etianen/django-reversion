from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType

try:
    from is_core.filters.default_filters import DefaultFilter
except ImportError:
    DefaultFilter = object


class VersionIDFilter(DefaultFilter):
    widget = forms.TextInput()

    def get_filter_term(self, request):
        self._check_suffix()
        return {''.join((self.get_filter_prefix(), 'versions__object_id')): self.value}


class VersionContextTypeFilter(DefaultFilter):
    ALL_LABEL = '--------'
    ALL_SLUG = '__all__'

    def get_widget(self):
        from reversion.models import AuditLog

        if self.widget:
            return self.widget

        formfield = forms.ModelChoiceField(queryset=ContentType.objects.filter(
            pk__in=AuditLog.objects.all().values('versions__content_type')))
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
