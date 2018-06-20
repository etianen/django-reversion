from test_app.models import TestModel
from test_app.tests.base import TestBase, TestModelMixin, LoginMixin


class CreateRevisionTest(TestModelMixin, TestBase):

    def testCreateRevision(self):
        response = self.client.post("/test-app/create-revision/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,))

    def testCreateRevisionGet(self):
        self.client.get("/test-app/create-revision/")
        self.assertNoRevision()


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

    def testRevisionMixinCustomPredicate(self):
        self.client.post("/test-app/revision-mixin/", HTTP_X_NOREVISION="true")
        self.assertNoRevision()


class RevisionMixinUserTest(LoginMixin, TestModelMixin, TestBase):

    def testCreateRevisionUser(self):
        response = self.client.post("/test-app/revision-mixin/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,), user=self.user)
