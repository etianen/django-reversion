from io import StringIO
from django.core.management import call_command
from test_app.models import TestModel
from test_app.tests.base import TestBase


class CreateInitialRevisionTest(TestBase):

    def testCreateInitialRevisions(self):
        obj = TestModel.objects.create()
        call_command("createinitialrevisions", verbosity=2, stdout=StringIO(), stderr=StringIO())
        self.assertSingleRevision((obj,), comment="Initial version.")
