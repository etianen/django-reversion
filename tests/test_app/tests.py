from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
import reversion
from reversion.models import Version
from test_app.models import TestModel, TestMeta


class ReversionTestBase(TestCase):

    multi_db = True

    def assertRevisionCreated(self, *objects, user=None, comment="", meta_names=(), date_created=None, db=None,
                              count=1):
        version_set = reversion.get_for_object(objects[0], db=db)
        self.assertEqual(len(version_set), count)
        for version in version_set:
            revision = version.revision
            self.assertEqual(revision.user, user)
            self.assertEqual(revision.comment, comment)
            self.assertAlmostEqual(revision.date_created, date_created or timezone.now(), delta=timedelta(seconds=1))
            # Check meta.
            self.assertEqual(revision.testmeta_set.count(), len(meta_names))
            for meta_name in meta_names:
                self.assertTrue(revision.testmeta_set.filter(name=meta_name).exists())
            # Check remaining objects.
            self.assertEqual(revision.version_set.count(), len(objects))
            for obj in objects:
                self.assertTrue(reversion.get_for_object(obj, db=db).filter(revision=revision).exists())

    def assertRevisionNotCreated(self, obj, db=None):
        self.assertRevisionCreated(obj, db=db, count=0)


class RevisionAPITest(ReversionTestBase):

    def testRevisionCreated(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertRevisionCreated(obj)

    def testRevisionCreatedNested(self):
        with reversion.create_revision():
            with reversion.create_revision():
                obj = TestModel.objects.create()
        self.assertRevisionCreated(obj)

    def testRevisionCreatedMultiDb(self):
        with reversion.create_revision(db="mysql"), reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        self.assertRevisionCreated(obj, db="mysql")
        self.assertRevisionCreated(obj, db="postgres")

    def testRevisionNotCreatedEmptyRevisionBlock(self):
        with reversion.create_revision():
            pass
        self.assertEqual(Version.objects.count(), 0)

    def testRevisionNotCreatedException(self):
        try:
            with reversion.create_revision():
                obj = TestModel.objects.create()
                raise Exception("Boom!")
        except:
            pass
        self.assertRevisionNotCreated(obj)

    def testRevisionNotCreatedNoBlock(self):
        obj = TestModel.objects.create()
        self.assertRevisionNotCreated(obj)

    # Ignore duplicates.

    def testGetSetIgnoreDuplicates(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.save()
            self.assertEqual(reversion.get_ignore_duplicates(), False)
            reversion.set_ignore_duplicates(True)
            self.assertEqual(reversion.get_ignore_duplicates(), True)
        self.assertRevisionCreated(obj, count=1)


class MetadataAPITest(ReversionTestBase):

    def testGetSetComment(self):
        comment = "comment v1"
        with reversion.create_revision():
            obj = TestModel.objects.create()
            self.assertEqual(reversion.get_comment(), "")
            reversion.set_comment(comment)
            self.assertEqual(reversion.get_comment(), comment)
        self.assertRevisionCreated(obj, comment=comment)

    def testGetSetUser(self):
        user = User.objects.create(username="test")
        with reversion.create_revision():
            obj = TestModel.objects.create()
            self.assertEqual(reversion.get_user(), None)
            reversion.set_user(user)
            self.assertEqual(reversion.get_user(), user)
        self.assertRevisionCreated(obj, user=user)

    def testAddMeta(self):
        meta_name = "meta v1"
        with reversion.create_revision():
            obj = TestModel.objects.create()
            reversion.add_meta(TestMeta, name=meta_name)
        self.assertRevisionCreated(obj, meta_names=(meta_name,))

    def testAddMetaMultDb(self):
        meta_name = "meta v1"
        with reversion.create_revision(db="mysql"), reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
            reversion.add_meta(TestMeta, name=meta_name)
        self.assertRevisionCreated(obj, meta_names=(meta_name,), db="mysql")
        self.assertRevisionCreated(obj, meta_names=(meta_name,), db="postgres")


class RawRevisionAPITest(ReversionTestBase):

    def testSaveRevision(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,))
        self.assertRevisionCreated(obj)

    def testSaveRevisionDb(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), db="postgres")
        self.assertRevisionCreated(obj, db="postgres")

    def testSaveRevisionComment(self):
        comment = "comment v1"
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), comment=comment)
        self.assertRevisionCreated(obj, comment=comment)

    def testSaveRevisionUser(self):
        user = User.objects.create(username="test")
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), user=user)
        self.assertRevisionCreated(obj, user=user)

    def testSaveRevisionMeta(self):
        meta_name = "meta v1"
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), meta=(reversion.RevisionMeta(TestMeta, name=meta_name),))
        self.assertRevisionCreated(obj, meta_names=(meta_name,))

    def testSaveRevisionMetaDb(self):
        meta_name = "meta v1"
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), meta=(reversion.RevisionMeta(TestMeta, name=meta_name),), db="postgres")
        self.assertRevisionCreated(obj, meta_names=(meta_name,), db="postgres")

    def testSaveRevisionIgnoreDuplicates(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), ignore_duplicates=True)
        reversion.save_revision((obj,), ignore_duplicates=True)
        self.assertRevisionCreated(obj, count=1)
