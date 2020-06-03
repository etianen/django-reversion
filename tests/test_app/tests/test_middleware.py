from django.conf import settings
from django.test.utils import override_settings
from test_app.models import TestModel
from test_app.tests.base import TestBase, TestModelMixin, LoginMixin


use_middleware = override_settings(
    MIDDLEWARE=settings.MIDDLEWARE + ["reversion.middleware.RevisionMiddleware"],
)


@use_middleware
class RevisionMiddlewareTest(TestModelMixin, TestBase):

    def testCreateRevision(self):
        response = self.client.post("/test-app/save-obj/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,))

    def testCreateRevisionError(self):
        with self.assertRaises(Exception):
            self.client.post("/test-app/save-obj-error/")
        self.assertNoRevision()

    @override_settings(REVERSION_ROLLBACK_COND_FUNC=lambda response: False)
    def testCreateRevisionChangeCondition(self):
        self.client.post("/test-app/save-obj-but-send-403/")
        obj = TestModel.objects.last()
        self.assertSingleRevision((obj,))

    def testCreateRevisionGet(self):
        self.client.get("/test-app/create-revision/")
        self.assertNoRevision()


@use_middleware
class RevisionMiddlewareUserTest(TestModelMixin, LoginMixin, TestBase):

    def testCreateRevisionUser(self):
        response = self.client.post("/test-app/save-obj/")
        obj = TestModel.objects.get(pk=response.content)
        self.assertSingleRevision((obj,), user=self.user)
