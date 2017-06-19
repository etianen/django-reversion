from django.forms.models import modelform_factory

import reversion
from reversion.models import Version

from .base import TestBase, TestModelMixin
from ..models import TestModel, TestModelRelated


class ModelFormSaveTest(TestModelMixin, TestBase):

    def test_model_form_saving_with_m2m(self):
        v1 = TestModelRelated.objects.create(name="v1")
        v2 = TestModelRelated.objects.create(name="v2")
        obj = TestModel.objects.create()
        form_class = modelform_factory(TestModel, fields=('name', 'related'))
        form = form_class(instance=obj, data={'name': 'My Name', 'related': [v1.pk, v2.pk]})
        self.assertTrue(form.is_valid())
        with reversion.create_revision():
            obj = form.save()
        version = Version.objects.get_for_object(obj).first()
        self.assertEqual(set(version.field_dict['related']), {v1.pk, v2.pk})
