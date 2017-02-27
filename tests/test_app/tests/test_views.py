from test_app.models import TestModel
from test_app.tests.base import TestBase, TestBaseTransaction, TestModelMixin, LoginMixin


class CreateRevisionTest(TestModelMixin, TestBase):

    def testCreateRevision(self):
        response = self.client.post("/test-app/create-revision/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,))

    def testCreateRevisionGet(self):
        self.client.get("/test-app/create-revision/")
        self.assertNoRevision()


class RevisionAtomicTest(TestModelMixin, TestBaseTransaction):

    def testRevisionAtomic(self):
        is_atomic = self.client.post("/test-app/atomic-revision/").content
        self.assertEqual(is_atomic, b'True')

    def testRevisionNonAtomic(self):
        is_atomic = self.client.post("/test-app/non-atomic-revision/").content
        self.assertEqual(is_atomic, b'False')


class CreateRevisionUserTest(LoginMixin, TestModelMixin, TestBase):

    def testCreateRevisionUser(self):
        response = self.client.post("/test-app/create-revision/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,), user=self.user)


class RevisionMixinTest(TestModelMixin, TestBase):

    def testRevisionMixin(self):
        response = self.client.post("/test-app/revision-mixin/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,))

    def testRevisionMixinGet(self):
        self.client.get("/test-app/revision-mixin/")
        self.assertNoRevision()


class RevisionAtomicMixinTest(TestModelMixin, TestBaseTransaction):

    def testRevisionMixinAtomic(self):
        is_atomic = self.client.post("/test-app/revision-mixin-atomic/").content
        self.assertEqual(is_atomic, b'True')

    def testRevisionMixinNonAtomic(self):
        is_atomic = self.client.post("/test-app/revision-mixin-non-atomic/").content
        self.assertEqual(is_atomic, b'False')


class RevisionMixinUserTest(LoginMixin, TestModelMixin, TestBase):

    def testCreateRevisionUser(self):
        response = self.client.post("/test-app/revision-mixin/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,), user=self.user)
