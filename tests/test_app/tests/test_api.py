from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
import reversion
from test_app.models import TestModel, TestModelParent, TestMeta
from test_app.tests.base import TestBase, UserTestBase


class DefaultTest(TestBase):

    def testModelSave(self):
        TestModel.objects.create()
        self.assertNoRevision()


class IsRegisteredTest(TestBase):

    def testIsRegistered(self):
        self.assertTrue(reversion.is_registered(TestModel))

    def testIsRegisteredFalse(self):
        self.assertFalse(reversion.is_registered(User))


class GetRegisteredModelsTest(TestBase):

    def testGetRegisteredModels(self):
        self.assertEqual(set(reversion.get_registered_models()), set((TestModel, TestModelParent,)))


class RegisterTest(TestBase):

    def testRegisterDecorator(self):
        reversion.unregister(TestModel)
        reversion.register()(TestModel)
        self.assertTrue(reversion.is_registered(TestModel))

    def testRegisterAlreadyRegistered(self):
        with self.assertRaises(reversion.RegistrationError):
            reversion.register(TestModel)


class UnregisterTest(TestBase):

    def testUnregister(self):
        reversion.unregister(TestModel)
        self.assertFalse(reversion.is_registered(TestModel))

    def testUnregisterNotRegistered(self):
        with self.assertRaises(reversion.RegistrationError):
            reversion.unregister(User)


class CreateRevisionTest(TestBase):

    def testCreateRevision(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertSingleRevision((obj,))

    def testCreateRevisionNested(self):
        with reversion.create_revision():
            with reversion.create_revision():
                obj = TestModel.objects.create()
        self.assertSingleRevision((obj,))

    def testCreateRevisionEmpty(self):
        with reversion.create_revision():
            pass
        self.assertNoRevision()

    def testCreateRevisionException(self):
        try:
            with reversion.create_revision():
                TestModel.objects.create()
                raise Exception("Boom!")
        except:
            pass
        self.assertNoRevision()

    def testCreateRevisionDecorator(self):
        obj = reversion.create_revision()(TestModel.objects.create)()
        self.assertSingleRevision((obj,))


class CreateRevisionManageManuallyTest(TestBase):

    def testCreateRevisionManageManually(self):
        with reversion.create_revision(manage_manually=True):
            TestModel.objects.create()
        self.assertNoRevision()

    def testCreateRevisionManageManuallyNested(self):
        with reversion.create_revision():
            with reversion.create_revision(manage_manually=True):
                TestModel.objects.create()
        self.assertNoRevision()


class CreateRevisionDbTest(TestBase):

    def testCreateRevisionMultiDb(self):
        with reversion.create_revision(using="mysql"), reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertNoRevision()
        self.assertSingleRevision((obj,), using="mysql")
        self.assertSingleRevision((obj,), using="postgres")


class CreateRevisionFollowTest(TestBase):

    def testCreateRevisionFollow(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, follow=("related_instances",))
        obj_2 = TestModel.objects.create()
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
            obj_1.related_instances.add(obj_2)
        self.assertSingleRevision((obj_1, obj_2))

    def testCreateRevisionFollowInvalid(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, follow=("name",))
        with reversion.create_revision():
            with self.assertRaises(reversion.RegistrationError):
                TestModel.objects.create()


class CreateRevisionIgnoreDuplicatesTest(TestBase):

    def testCreateRevisionIgnoreDuplicates(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, ignore_duplicates=True)
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.save()
        self.assertSingleRevision((obj,))


class CreateRevisionInheritanceTest(TestBase):

    def testCreateRevisionInheritance(self):
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        self.assertSingleRevision((obj, obj.testmodel_ptr))


class SetCommentTest(TestBase):

    def testSetComment(self):
        with reversion.create_revision():
            reversion.set_comment("comment v1")
            obj = TestModel.objects.create()
        self.assertSingleRevision((obj,), comment="comment v1")

    def testSetCommentNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.set_comment("comment v1")


class GetCommentTest(TestBase):

    def testGetComment(self):
        with reversion.create_revision():
            reversion.set_comment("comment v1")
            self.assertEqual(reversion.get_comment(), "comment v1")

    def testGetCommentDefault(self):
        with reversion.create_revision():
            self.assertEqual(reversion.get_comment(), "")

    def testGetCommentNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.get_comment()


class SetUserTest(UserTestBase):

    def testSetUser(self):
        with reversion.create_revision():
            reversion.set_user(self.user)
            obj = TestModel.objects.create()
        self.assertSingleRevision((obj,), user=self.user)

    def testSetUserNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.set_user(self.user)


class GetUserTest(UserTestBase):

    def testGetUser(self):
        with reversion.create_revision():
            reversion.set_user(self.user)
            self.assertEqual(reversion.get_user(), self.user)

    def testGetUserDefault(self):
        with reversion.create_revision():
            self.assertEqual(reversion.get_user(), None)

    def testGetUserNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.get_user()


class SetDateCreatedTest(TestBase):

    def testSetDateCreated(self):
        date_created = timezone.now() - timedelta(days=20)
        with reversion.create_revision():
            reversion.set_date_created(date_created)
            obj = TestModel.objects.create()
        self.assertSingleRevision((obj,), date_created=date_created)

    def testDateCreatedNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.set_date_created(timezone.now())


class GetDateCreatedTest(TestBase):

    def testGetDateCreated(self):
        date_created = timezone.now() - timedelta(days=20)
        with reversion.create_revision():
            reversion.set_date_created(date_created)
            self.assertEqual(reversion.get_date_created(), date_created)

    def testGetDateCreatedDefault(self):
        with reversion.create_revision():
            self.assertAlmostEqual(reversion.get_date_created(), timezone.now(), delta=timedelta(seconds=1))

    def testGetDateCreatedNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.get_date_created()


class AddMetaTest(TestBase):

    def testAddMeta(self):
        with reversion.create_revision():
            reversion.add_meta(TestMeta, name="meta v1")
            obj = TestModel.objects.create()
        self.assertSingleRevision((obj,), meta_names=("meta v1",))

    def testAddMetaNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.add_meta(TestMeta, name="meta v1")

    def testAddMetaMultDb(self):
        with reversion.create_revision(using="mysql"), reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
            reversion.add_meta(TestMeta, name="meta v1")
        self.assertNoRevision()
        self.assertSingleRevision((obj,), meta_names=("meta v1",), using="mysql")
        self.assertSingleRevision((obj,), meta_names=("meta v1",), using="postgres")
