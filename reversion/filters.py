from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType

try:
    from pyston.filters.default_filters import SimpleMethodEqualFilter
    from is_core.filters import UIFilterMixin
    from is_core.forms.models import ModelChoiceField
except ImportError:
    SimpleModelFieldEqualFilter = object
    UIFilterMixin = object
    from django.forms import ModelChoiceField


class RelatedObjectsFilter(SimpleMethodEqualFilter):

    widget = forms.TextInput()

    def get_filter_term(self, value, operator, request):
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


class RelatedObjectsWithIntIdFilter(SimpleMethodEqualFilter):

    def get_filter_term(self, value, operator, request):
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


class VersionIDFilter(SimpleMethodEqualFilter):

    def get_filter_term(self, value, operator, request):
        return {'versions__object_id': value}


class VersionContextTypeFilter(UIFilterMixin, SimpleMethodEqualFilter):

    def get_widget(self, request):
        if self.widget:
            return self.widget

        formfield = ModelChoiceField(queryset=ContentType.objects.all())
        formfield.choices = list(formfield.choices)
        if not formfield.choices[0][0]:
            del formfield.choices[0]
        formfield.choices.insert(0, ('', ''))
        return formfield.widget

    def get_filter_term(self, value, operator, request):
        return {'versions__content_type': value}
