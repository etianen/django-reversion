from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Value
from django.db.models.functions import Concat

import reversion
from reversion.models import Version
from test_app.models import TestModel, TestModelCustomObjectId, TestModelGenericInline
from test_app.tests.base import TestBase


class ExpressionVersionTest(TestBase):

    databases = {"default"}

    def testIntegerExpressionCanBeReverted(self):
        reversion.register(TestModelGenericInline)
        obj = TestModelGenericInline.objects.create(
            object_id=10, content_type=ContentType.objects.get_for_model(TestModel),
        )
        with reversion.create_revision():
            obj.object_id = F("object_id") + 1
            obj.content_type_id = F("content_type_id")
            obj.save()
        version = Version.objects.get_for_object(obj).get()
        self.assertEqual(version.field_dict["object_id"], 11)
        TestModelGenericInline.objects.filter(pk=obj.pk).update(object_id=99)
        version.revert()
        obj.refresh_from_db()
        self.assertEqual(obj.object_id, 11)

    def testCustomObjectIdExpression(self):
        reversion.register(TestModelCustomObjectId, fields=("name",), object_id_field="slug")
        obj = TestModelCustomObjectId.objects.create(slug="before", name="value")
        with reversion.create_revision():
            obj.slug = Concat(F("slug"), Value("-after"))
            obj.save()
        version = Version.objects.get_for_object_reference(TestModelCustomObjectId, "before-after").get()
        self.assertEqual(version.object_id, "before-after")
        self.assertEqual(version.field_dict, {"name": "value"})

    def testStringExpressionCanBeReverted(self):
        reversion.register(TestModel)
        obj = TestModel.objects.create(name="before")
        with reversion.create_revision():
            obj.name = Concat(F("name"), Value(" after"))
            obj.save()
        version = Version.objects.get_for_object(obj).get()
        self.assertEqual(version.field_dict["name"], "before after")
        TestModel.objects.filter(pk=obj.pk).update(name="later")
        version.revert()
        obj.refresh_from_db()
        self.assertEqual(obj.name, "before after")

    def testManualAddPreservesTheOriginalInstance(self):
        reversion.register(TestModelGenericInline)
        obj = TestModelGenericInline.objects.create(
            object_id=10, content_type=ContentType.objects.get_for_model(TestModel),
        )
        expression = F("object_id") + 1
        obj.object_id = expression
        obj.inline_name = "unsaved"
        with reversion.create_revision(manage_manually=True):
            reversion.add_to_revision(obj)
        version = Version.objects.get_for_object(obj).get()
        self.assertEqual(version.field_dict["object_id"], 10)
        self.assertEqual(version.field_dict["inline_name"], "unsaved")
        self.assertIs(obj.object_id, expression)
        self.assertEqual(obj.inline_name, "unsaved")

    def testExcludedExpressionsDoNotRequireReloading(self):
        reversion.register(TestModel, fields=("id",))
        obj = TestModel.objects.create()
        obj.name = F("name")
        with reversion.create_revision(manage_manually=True):
            # Populate the content-type cache before measuring serialization.
            ContentType.objects.get_for_model(TestModel)
            with self.assertNumQueries(0):
                reversion.add_to_revision(obj)
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {"id": obj.pk})
