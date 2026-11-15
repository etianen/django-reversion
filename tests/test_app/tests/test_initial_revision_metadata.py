from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management import CommandError
from django.test import override_settings

from test_app.models import TestModel
from test_app.tests.base import TestBase, TestModelMixin


class CreateInitialRevisionMetadataTest(TestModelMixin, TestBase):

    def testUser(self):
        user = get_user_model().objects.create_user(username="historian")
        obj = TestModel.objects.create()

        self.callCommand("createinitialrevisions", "--user", user.get_username())

        self.assertSingleRevision((obj,), user=user, comment="Initial version.")

    def testUnknownUserDoesNotCreateRevisions(self):
        TestModel.objects.create()

        with self.assertRaisesMessage(CommandError, "Unknown user"):
            self.callCommand("createinitialrevisions", "--user", "missing")

        self.assertNoRevision()

    def testUserComesFromRevisionDatabase(self):
        user = get_user_model().objects.db_manager("postgres").create_user(username="historian")
        obj = TestModel.objects.create()

        self.callCommand("createinitialrevisions", "--user", user.get_username(), using="postgres")

        self.assertSingleRevision((obj,), user=user, comment="Initial version.", using="postgres")
        self.assertNoRevision()

    def testUserAndTimestampApplyToEveryBatch(self):
        user = get_user_model().objects.create_user(username="historian")
        objects = [TestModel.objects.create(), TestModel.objects.create()]
        timestamp = "2020-09-28T12:34:56+02:00"

        self.callCommand(
            "createinitialrevisions", "--user", user.get_username(),
            "--date-created", timestamp, batch_size=1,
        )

        for obj in objects:
            self.assertSingleRevision(
                (obj,), user=user, comment="Initial version.", date_created=datetime.fromisoformat(timestamp),
            )

    @override_settings(TIME_ZONE="Etc/GMT-2")
    def testNaiveTimestampUsesDefaultTimeZone(self):
        obj = TestModel.objects.create()

        self.callCommand("createinitialrevisions", "--date-created", "2020-09-28T12:34:56")

        self.assertSingleRevision(
            (obj,), comment="Initial version.", date_created=datetime.fromisoformat("2020-09-28T12:34:56+02:00"),
        )

    @override_settings(USE_TZ=False, TIME_ZONE="Etc/GMT-2")
    def testAwareTimestampWithoutTimeZoneSupport(self):
        obj = TestModel.objects.create()

        self.callCommand("createinitialrevisions", "--date-created", "2020-09-28T12:34:56Z")

        self.assertSingleRevision(
            (obj,), comment="Initial version.", date_created=datetime(2020, 9, 28, 14, 34, 56),
        )

    def testInvalidTimestampDoesNotCreateRevisions(self):
        TestModel.objects.create()

        for timestamp in ("not-a-date", "2020-02-30T12:00:00", "2020-09-28T24:00:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesMessage(CommandError, "Invalid --date-created"):
                    self.callCommand("createinitialrevisions", "--date-created", timestamp)
                self.assertNoRevision()
