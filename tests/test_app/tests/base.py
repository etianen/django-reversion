from datetime import timedelta
from importlib import import_module, reload
from io import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import clear_url_caches
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import timezone

import reversion
from reversion.models import Revision, Version
from test_app.models import TestModel, TestModelParent


# Test helpers.

class TestBaseMixin:

    databases = "__all__"

    def reloadUrls(self):
        reload(import_module(settings.ROOT_URLCONF))
        clear_url_caches()

    def setUp(self):
        super().setUp()
        for model in list(reversion.get_registered_models()):
            reversion.unregister(model)

    def tearDown(self):
        super().tearDown()
        for model in list(reversion.get_registered_models()):
            reversion.unregister(model)

    def callCommand(self, command, *args, **kwargs):
        kwargs.setdefault("stdout", StringIO())
        kwargs.setdefault("stderr", StringIO())
        kwargs.setdefault("verbosity", 2)
        return call_command(command, *args, **kwargs)

    def assertSingleRevision(self, objects, user=None, comment="", meta_names=(), date_created=None,
                             using=None, model_db=None):
        revision = Version.objects.using(using).get_for_object(objects[0], model_db=model_db).get().revision
        self.assertEqual(revision.user, user)
        if hasattr(comment, 'pattern'):
            self.assertRegex(revision.get_comment(), comment)
        elif comment is not None:  # Allow a wildcard comment.
            self.assertEqual(revision.get_comment(), comment)
        self.assertAlmostEqual(revision.date_created, date_created or timezone.now(), delta=timedelta(seconds=1))
        # Check meta.
        self.assertEqual(revision.testmeta_set.count(), len(meta_names))
        for meta_name in meta_names:
            self.assertTrue(revision.testmeta_set.filter(name=meta_name).exists())
        # Check objects.
        self.assertEqual(revision.version_set.count(), len(objects))
        for obj in objects:
            self.assertTrue(Version.objects.using(using).get_for_object(
                obj,
                model_db=model_db,
            ).filter(
                revision=revision,
            ).exists())

    def assertNoRevision(self, using=None):
        self.assertEqual(Revision.objects.using(using).all().count(), 0)


class TestBase(TestBaseMixin, TestCase):
    pass


class TestBaseTransaction(TestBaseMixin, TransactionTestCase):
    pass


class TestModelMixin:

    def setUp(self):
        super().setUp()
        reversion.register(TestModel)


class TestModelParentMixin(TestModelMixin):

    def setUp(self):
        super().setUp()
        reversion.register(TestModelParent, follow=("testmodel_ptr",))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserMixin(TestBase):

    def setUp(self):
        super().setUp()
        self.user = User(username="test", is_staff=True, is_superuser=True)
        self.user.set_password("password")
        self.user.save()


class LoginMixin(UserMixin):

    def setUp(self):
        super().setUp()
        self.client.login(username="test", password="password")
