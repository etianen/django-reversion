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
