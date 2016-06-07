from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
import reversion
from reversion.models import Revision


# Test helpers.

class TestBase(TestCase):

    multi_db = True

    def assertSingleRevision(self, objects, user=None, comment="", meta_names=(), date_created=None, db=None):
        revision = Revision.objects.using(db).get()
        self.assertEqual(revision.user, user)
        self.assertEqual(revision.comment, comment)
        self.assertAlmostEqual(revision.date_created, date_created or timezone.now(), delta=timedelta(seconds=1))
        # Check meta.
        self.assertEqual(revision.testmeta_set.count(), len(meta_names))
        for meta_name in meta_names:
            self.assertTrue(revision.testmeta_set.filter(name=meta_name).exists())
        # Check objects.
        self.assertEqual(revision.version_set.count(), len(objects))
        for obj in objects:
            self.assertTrue(reversion.get_for_object(obj, db=db).filter(revision=revision).exists())

    def assertNoRevision(self, db=None):
        self.assertEqual(Revision.objects.using(db).all().count(), 0)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserTestBase(TestBase):

    def setUp(self):
        super(UserTestBase, self).setUp()
        self.user = User(username="test", is_staff=True, is_superuser=True)
        self.user.set_password("password")
        self.user.save()


class LoginTestBase(UserTestBase):

    def setUp(self):
        super(LoginTestBase, self).setUp()
        self.client.login(username="test", password="password")
