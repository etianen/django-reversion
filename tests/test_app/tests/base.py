from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
try:
    from django.urls import clear_url_caches
except ImportError:  # Django < 1.10 pragma: no cover
    from django.core.urlresolvers import clear_url_caches
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.six import StringIO, assertRegex
import reversion
from reversion.models import Revision, Version
from test_app.models import TestModel, TestModelParent
from importlib import import_module
try:
    from importlib import reload
except ImportError:  # Python 2.7
    pass


# Test helpers.

class TestBaseMixin(object):

    multi_db = True

    def reloadUrls(self):
        reload(import_module(settings.ROOT_URLCONF))
        clear_url_caches()

    def tearDown(self):
        super(TestBaseMixin, self).tearDown()
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
            assertRegex(self, revision.comment, comment)
        elif comment is not None:  # Allow a wildcard comment.
            self.assertEqual(revision.comment, comment)
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


class TestModelMixin(object):

    def setUp(self):
        super(TestModelMixin, self).setUp()
        reversion.register(TestModel)


class TestModelParentMixin(TestModelMixin):

    def setUp(self):
        super(TestModelParentMixin, self).setUp()
        reversion.register(TestModelParent, follow=("testmodel_ptr",))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserMixin(TestBase):

    def setUp(self):
        super(UserMixin, self).setUp()
        self.user = User(username="test", is_staff=True, is_superuser=True)
        self.user.set_password("password")
        self.user.save()


class LoginMixin(UserMixin):

    def setUp(self):
        super(LoginMixin, self).setUp()
        self.client.login(username="test", password="password")
