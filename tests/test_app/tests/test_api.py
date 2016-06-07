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


class GetAdapterTest(TestBase):

    def testGetAdapter(self):
        self.assertIsInstance(reversion.get_adapter(TestModel), reversion.VersionAdapter)

    def testGetAdapterUnregistered(self):
        with self.assertRaises(reversion.RegistrationError):
            reversion.get_adapter(TestModelUnregistered)


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
        with reversion.create_revision(db="mysql"), reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        self.assertNoRevision()
        self.assertSingleRevision((obj,), db="mysql")
        self.assertSingleRevision((obj,), db="postgres")


class SetIgnoreDuplicatesTest(TestBase):

    def testSetIgnoreDuplicates(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.save()
            reversion.set_ignore_duplicates(True)
        self.assertSingleRevision((obj,))

    def testSetIgnoreDuplicatesNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.set_ignore_duplicates(True)


class GetIgnoreDuplicatesTest(TestBase):

    def testGetIgnoreDuplicates(self):
        with reversion.create_revision():
            reversion.set_ignore_duplicates(True)
            self.assertEqual(reversion.get_ignore_duplicates(), True)

    def testGetIgnoreDuplicatesDefault(self):
        with reversion.create_revision():
            self.assertEqual(reversion.get_ignore_duplicates(), False)

    def testGetIgnoreDuplicatesNoBlock(self):
        with self.assertRaises(reversion.RevisionManagementError):
            reversion.get_ignore_duplicates()


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
        with reversion.create_revision(db="mysql"), reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
            reversion.add_meta(TestMeta, name="meta v1")
        self.assertNoRevision()
        self.assertSingleRevision((obj,), meta_names=("meta v1",), db="mysql")
        self.assertSingleRevision((obj,), meta_names=("meta v1",), db="postgres")


class SaveRevisionTest(TestBase):

    def testSaveRevision(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,))
        self.assertSingleRevision((obj,))

    def testSaveRevisionEmpty(self):
        reversion.save_revision(())
        self.assertNoRevision()


class SaveRevisionDbTest(TestBase):

    def testSaveRevisionDb(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), db="postgres")
        self.assertNoRevision()
        self.assertSingleRevision((obj,), db="postgres")


class SaveRevisionCommentTest(TestBase):

    def testSaveRevisionComment(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), comment="comment v1")
        self.assertSingleRevision((obj,), comment="comment v1")


class SaveRevisionUserTest(UserTestBase):

    def testSaveRevisionUser(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), user=self.user)
        self.assertSingleRevision((obj,), user=self.user)


class SaveRevisionMetaTest(TestBase):

    def testSaveRevisionMeta(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,), meta=(reversion.RevisionMeta(TestMeta, name="meta v1"),))
        self.assertSingleRevision((obj,), meta_names=("meta v1",))


class SaveRevisionIgnoreDuplicatesTest(TestBase):

    def testSaveRevisionIgnoreDuplicates(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,))
        reversion.save_revision((obj,), ignore_duplicates=True)
        self.assertSingleRevision((obj,))


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
        with reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object(obj).count(), 0)
        self.assertEqual(reversion.get_for_object(obj, db="postgres").count(), 1)


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
        with reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(reversion.get_for_object_reference(TestModel, obj.pk, db="postgres").count(), 1)


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
        with reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 0)
        self.assertEqual(reversion.get_deleted(TestModel, db="postgres").count(), 1)


class GetDeletedModelDbTest(TestBase):

    def testGetDeletedModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        obj.delete()
        self.assertEqual(reversion.get_deleted(TestModel).count(), 0)
        self.assertEqual(reversion.get_deleted(TestModel, model_db="postgres").count(), 1)
