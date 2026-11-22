from django.db import models
from django.test.utils import isolate_apps

import reversion
from reversion.models import Version, _safe_subquery
from test_app.models import TestModel
from test_app.tests.base import TestBase, TestModelMixin


class SafeSubqueryQuotedTableTest(TestModelMixin, TestBase):

    databases = {"default"}

    @isolate_apps("test_app")
    def testQuotedModelTable(self):
        class QuotedModel(models.Model):
            class Meta:
                app_label = "test_app"
                db_table = '"{}"'.format(TestModel._meta.db_table)
                managed = False

        with reversion.create_revision():
            kept = TestModel.objects.create()
            deleted = TestModel.objects.create()
        kept_version = Version.objects.get_for_object(kept).get()
        deleted_version = Version.objects.get_for_object(deleted).get()
        deleted.delete()
        for method, expected in (("filter", kept_version), ("exclude", deleted_version)):
            with self.subTest(method=method):
                query = _safe_subquery(
                    method, Version.objects.all(), "object_id", QuotedModel.objects.all(), "id",
                )
                self.assertEqual(list(query), [expected])

    @isolate_apps("test_app")
    def testQuotedVersionTable(self):
        class QuotedVersion(models.Model):
            object_id = models.CharField(max_length=191)

            class Meta:
                app_label = "test_app"
                db_table = '"{}"'.format(Version._meta.db_table)
                managed = False

        with reversion.create_revision():
            recorded = TestModel.objects.create()
        unrecorded = TestModel.objects.create()
        for method, expected in (("filter", recorded), ("exclude", unrecorded)):
            with self.subTest(method=method):
                query = _safe_subquery(
                    method, TestModel.objects.all(), "id", QuotedVersion.objects.all(), "object_id",
                )
                self.assertEqual(list(query), [expected])
