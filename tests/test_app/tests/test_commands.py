from django.core.management import CommandError
from test_app.models import TestModel
from test_app.tests.base import TestBase


class CreateInitialRevisionTest(TestBase):

    def testCreateInitialRevisions(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions")
        self.assertSingleRevision((obj,), comment="Initial version.")

    def testCreateInitialRevisionsAlreadyCreated(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions")
        self.callCommand("createinitialrevisions")
        self.assertSingleRevision((obj,), comment="Initial version.")

    def testCreateInitialRevisionsAppLabel(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions", "test_app")
        self.assertSingleRevision((obj,), comment="Initial version.")

    def testCreateInitialRevisionsAppLabelMissing(self):
        with self.assertRaises(CommandError):
            self.callCommand("createinitialrevisions", "boom")

    def testCreateInitialRevisionsModel(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions", "test_app.TestModel")
        self.assertSingleRevision((obj,), comment="Initial version.")

    def testCreateInitialRevisionsModelMissing(self):
        with self.assertRaises(CommandError):
            self.callCommand("createinitialrevisions", "test_app.boom")

    def testCreateInitialRevisionsModelMissingApp(self):
        with self.assertRaises(CommandError):
            self.callCommand("createinitialrevisions", "boom.boom")

    def testCreateInitialRevisionsModelNotRegistered(self):
        TestModel.objects.create()
        self.callCommand("createinitialrevisions", "test_app.TestModelUnregistered")
        self.assertNoRevision()

    def testCreateInitialRevisionsDb(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions", db="postgres")
        self.assertNoRevision()
        self.assertSingleRevision((obj,), comment="Initial version.", db="postgres")

    def testCreateInitialRevisionsModelDb(self):
        obj = TestModel.objects.db_manager("postgres").create()
        self.callCommand("createinitialrevisions", model_db="postgres")
        self.assertSingleRevision((obj,), comment="Initial version.", model_db="postgres")

    def testCreateInitialRevisionsComment(self):
        obj = TestModel.objects.create()
        self.callCommand("createinitialrevisions", comment="comment v1")
        self.assertSingleRevision((obj,), comment="comment v1")
