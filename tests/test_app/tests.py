from django.contrib.auth.models import User
from django.test import TestCase
import reversion
from reversion.models import Revision, Version
from test_app.models import TestModel, TestMeta


class ApiTest(TestCase):

    multi_db = True

    def testRevisionCreatedInRevisionBlock(self):
        with reversion.create_revision():
            TestModel.objects.create()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 1)

    def testRevisionCreatedInNestedRevisionBlock(self):
        with reversion.create_revision():
            with reversion.create_revision():
                TestModel.objects.create()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 1)

    def testEmptyRevisionBlockCreatesNoRevision(self):
        with reversion.create_revision():
            pass
        self.assertEqual(Revision.objects.count(), 0)

    def testExceptionInRevisionBlockCreatesNoRevision(self):
        try:
            with reversion.create_revision():
                TestModel.objects.create()
                raise Exception("Boom!")
        except:
            pass
        self.assertEqual(Revision.objects.count(), 0)

    # Metadata.

    def testGetSetComment(self):
        comment = "v1 comment"
        with reversion.create_revision():
            TestModel.objects.create()
            self.assertEqual(reversion.get_comment(), "")
            reversion.set_comment(comment)
            self.assertEqual(reversion.get_comment(), comment)
        self.assertEqual(Revision.objects.get().comment, comment)

    def testGetSetUser(self):
        user = User.objects.create(username="test")
        with reversion.create_revision():
            TestModel.objects.create()
            self.assertEqual(reversion.get_user(), None)
            reversion.set_user(user)
            self.assertEqual(reversion.get_user(), user)
        self.assertEqual(Revision.objects.get().user, user)

    def testAddMeta(self):
        meta_name = "meta 1"
        with reversion.create_revision():
            TestModel.objects.create()
            reversion.add_meta(TestMeta, name=meta_name)
        self.assertEqual(TestMeta.objects.get().name, meta_name)

    # Multi-db tests.

    def testRevisionCreatedInMySQL(self):
        with reversion.create_revision(db="mysql"):
            TestModel.objects.create()
        self.assertEqual(Revision.objects.using("mysql").count(), 1)
        self.assertEqual(Version.objects.using("mysql").count(), 1)

    def testRevisionCreatedInPostgres(self):
        with reversion.create_revision(db="postgres"):
            TestModel.objects.create()
        self.assertEqual(Revision.objects.using("postgres").count(), 1)
        self.assertEqual(Version.objects.using("postgres").count(), 1)

    def testMultipleRevisionsCreatedInMultipleDatabases(self):
        with reversion.create_revision():
            with reversion.create_revision(db="mysql"):
                with reversion.create_revision(db="postgres"):
                    TestModel.objects.create()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 1)
        self.assertEqual(Revision.objects.using("mysql").count(), 1)
        self.assertEqual(Version.objects.using("mysql").count(), 1)
        self.assertEqual(Revision.objects.using("postgres").count(), 1)
        self.assertEqual(Version.objects.using("postgres").count(), 1)
