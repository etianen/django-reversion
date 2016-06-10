from datetime import timedelta
from django.utils import timezone
from django.utils.encoding import force_text
import reversion
from test_app.models import TestModel, TestModelUnregistered, TestMeta
from test_app.tests.base import TestBase, UserTestBase


class DefaultTest(TestBase):

    def testModelSave(self):
        TestModel.objects.create()
        self.assertNoRevision()


class IsRegisteredTest(TestBase):

    def testIsRegistered(self):
        self.assertTrue(reversion.is_registered(TestModel))

    def testIsRegisteredFalse(self):
        self.assertFalse(reversion.is_registered(TestModelUnregistered))


class GetRegisteredModelsTest(TestBase):

    def testGetRegisteredModels(self):
        self.assertEqual(list(reversion.get_registered_models()), [TestModel])


class RegisterTest(TestBase):

    def testRegister(self):
        revision_manager = reversion.RevisionManager("test")
        revision_manager.register(TestModelUnregistered)
        self.assertTrue(revision_manager.is_registered(TestModelUnregistered))

    def testRegisterAlreadyRegistered(self):
        with self.assertRaises(reversion.RegistrationError):
            reversion.register(TestModel)


class UnregisterTest(TestBase):

    def testUnregister(self):
        revision_manager = reversion.RevisionManager("test")
        revision_manager.register(TestModelUnregistered)
        revision_manager.unregister(TestModelUnregistered)
        self.assertFalse(reversion.is_registered(TestModelUnregistered))

    def testUnregisterNotRegistered(self):
        with self.assertRaises(reversion.RegistrationError):
            reversion.unregister(TestModelUnregistered)


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


class GetForObjectTest(TestBase):

    def testGetForObject(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object(obj).count(), 1)

    def testGetForObjectEmpty(self):
        obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object(obj).count(), 0)

    def testGetForObjectOrdering(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        self.assertEqual(reversion.get_for_object(obj)[0].field_dict["name"], "v2")
        self.assertEqual(reversion.get_for_object(obj)[1].field_dict["name"], "v1")

    def testGetForObjectFiltering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object(obj_1).get().object, obj_1)
        self.assertEqual(reversion.get_for_object(obj_2).get().object, obj_2)


class GetForObjectDbTest(TestBase):

    def testGetForObjectDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object(obj).count(), 0)
        self.assertEqual(reversion.get_for_object(obj, using="postgres").count(), 1)


class GetForObjectModelDbTest(TestBase):

    def testGetForObjectModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        self.assertEqual(reversion.get_for_object(obj).count(), 0)
        self.assertEqual(reversion.get_for_object(obj, model_db="postgres").count(), 1)


class GetForObjectReferenceTest(TestBase):

    def testGetForObjectReference(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk).count(), 1)

    def testGetForObjectReferenceEmpty(self):
        obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk).count(), 0)

    def testGetForObjectReferenceOrdering(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk)[0].field_dict["name"], "v2")
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk)[1].field_dict["name"], "v1")

    def testGetForObjectReferenceFiltering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj_1.pk).get().object, obj_1)
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj_2.pk).get().object, obj_2)


class GetForObjectReferenceDbTest(TestBase):

    def testGetForObjectReferenceModelDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk, using="postgres").count(), 1)


class GetForObjectReferenceModelDbTest(TestBase):

    def testGetForObjectReferenceModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk, model_db="postgres").count(), 1)


class GetDeletedTest(TestBase):

    def testGetDeleted(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 1)

    def testGetDeletedEmpty(self):
        with reversion.create_revision():
            TestModel.objects.create()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 0)

    def testGetDeletedOrdering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        pk_1 = obj_1.pk
        obj_1.delete()
        pk_2 = obj_2.pk
        obj_2.delete()
        self.assertEqual(reversion.get_deleted(TestModel)[0].object_id, force_text(pk_2))
        self.assertEqual(reversion.get_deleted(TestModel)[1].object_id, force_text(pk_1))


class GetDeletedDbTest(TestBase):

    def testGetDeletedDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 0)
        self.assertEqual(reversion.get_deleted(TestModel, using="postgres").count(), 1)


class GetDeletedModelDbTest(TestBase):

    def testGetDeletedModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        obj.delete()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 0)
        self.assertEqual(reversion.get_deleted(TestModel, model_db="postgres").count(), 1)
