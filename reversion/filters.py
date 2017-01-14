from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType


try:
    from is_core.filters.default_filters import DefaultMethodFilter
    from is_core.filters.exceptions import FilterException
    from is_core.forms.models import ModelChoiceField
except ImportError:
    DefaultMethodFilter = object
    FilterException = object
    from django.forms import ModelChoiceField


class RelatedObjectsFilter(DefaultMethodFilter):

    widget = forms.TextInput()

    def get_filter_term_without_prefix(self, value, suffix, request):
        if '|' not in value:
            return {
                'versions__object_id': value
            }
        else:
            content_type, object_id = value.split('|', 1)
            return {
                'versions__object_id': object_id,
                'versions__content_type': content_type
            }


class RelatedObjectsWithIntIdFilter(DefaultMethodFilter):

    widget = forms.TextInput()

    def get_filter_term_without_prefix(self, value, suffix, request):
        if '|' not in value:
            return {
                'versions__object_id_int': value
            }
        else:
            content_type, object_id = value.split('|', 1)
            return {
                'versions__object_id_int': object_id,
                'versions__content_type': content_type
            }


class VersionIDFilter(DefaultMethodFilter):
    widget = forms.TextInput()

    def get_filter_term_without_prefix(self, value, suffix, request):
        return {'versions__object_id': value}


class VersionContextTypeFilter(DefaultMethodFilter):

    ALL_LABEL = '--------'
    ALL_SLUG = '__all__'

    def get_widget(self, request):
        if self.widget:
            return self.widget

        formfield = ModelChoiceField(queryset=ContentType.objects.all())
        formfield.choices = list(formfield.choices)
        if not formfield.choices[0][0]:
            del formfield.choices[0]
        formfield.choices.insert(0, (self.ALL_SLUG, self.ALL_LABEL))
        return formfield.widget

    def get_filter_term_without_prefix(self, value, suffix, request):
        if not suffix:
            if value == self.ALL_SLUG:
                return {}

        return {'versions__content_type': value}
