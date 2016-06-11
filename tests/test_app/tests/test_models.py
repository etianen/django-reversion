from django.utils.encoding import force_text
import reversion
from reversion.models import Version
from test_app.models import TestModel, TestModelParent
from test_app.tests.base import TestBase


class GetForModelTest(TestBase):

    def testGetForModel(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_model(obj.__class__).count(), 1)


class GetForModelDbTest(TestBase):

    def testGetForModelDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.using("postgres").get_for_model(obj.__class__).count(), 1)

    def testGetForModelDbMySql(self):
        with reversion.create_revision(using="mysql"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.using("mysql").get_for_model(obj.__class__).count(), 1)


class GetForObjectTest(TestBase):

    def testGetForObject(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 1)

    def testGetForObjectEmpty(self):
        obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 0)

    def testGetForObjectOrdering(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        self.assertEqual(Version.objects.get_for_object(obj)[0].field_dict["name"], "v2")
        self.assertEqual(Version.objects.get_for_object(obj)[1].field_dict["name"], "v1")

    def testGetForObjectFiltering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj_1).get().object, obj_1)
        self.assertEqual(Version.objects.get_for_object(obj_2).get().object, obj_2)


class GetForObjectDbTest(TestBase):

    def testGetForObjectDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 0)
        self.assertEqual(Version.objects.using("postgres").get_for_object(obj).count(), 1)

    def testGetForObjectDbMySql(self):
        with reversion.create_revision(using="mysql"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 0)
        self.assertEqual(Version.objects.using("mysql").get_for_object(obj).count(), 1)


class GetForObjectModelDbTest(TestBase):

    def testGetForObjectModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 0)
        self.assertEqual(Version.objects.get_for_object(obj, model_db="postgres").count(), 1)


class GetForObjectUniqueTest(TestBase):

    def testGetForObjectUnique(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.save()
        self.assertEqual(len(list(Version.objects.get_for_object(obj).get_unique())), 1)

    def testGetForObjectUniqueMiss(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        self.assertEqual(len(list(Version.objects.get_for_object(obj).get_unique())), 2)


class GetForObjectReferenceTest(TestBase):

    def testGetForObjectReference(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 1)

    def testGetForObjectReferenceEmpty(self):
        obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 0)

    def testGetForObjectReferenceOrdering(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk)[0].field_dict["name"], "v2")
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk)[1].field_dict["name"], "v1")

    def testGetForObjectReferenceFiltering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj_1.pk).get().object, obj_1)
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj_2.pk).get().object, obj_2)


class GetForObjectReferenceDbTest(TestBase):

    def testGetForObjectReferenceModelDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(Version.objects.using("postgres").get_for_object_reference(TestModel, obj.pk).count(), 1)


class GetForObjectReferenceModelDbTest(TestBase):

    def testGetForObjectReferenceModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk, model_db="postgres").count(), 1)

    def testGetForObjectReferenceModelDbMySql(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("mysql").create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk, model_db="mysql").count(), 1)


class GetDeletedTest(TestBase):

    def testGetDeleted(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 1)

    def testGetDeletedEmpty(self):
        with reversion.create_revision():
            TestModel.objects.create()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 0)

    def testGetDeletedOrdering(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        with reversion.create_revision():
            obj_2 = TestModel.objects.create()
        pk_1 = obj_1.pk
        obj_1.delete()
        pk_2 = obj_2.pk
        obj_2.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel)[0].object_id, force_text(pk_2))
        self.assertEqual(Version.objects.get_deleted(TestModel)[1].object_id, force_text(pk_1))


class GetDeletedDbTest(TestBase):

    def testGetDeletedDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 0)
        self.assertEqual(Version.objects.using("postgres").get_deleted(TestModel).count(), 1)

    def testGetDeletedDbMySql(self):
        with reversion.create_revision(using="mysql"):
            obj = TestModel.objects.create()
        obj.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 0)
        self.assertEqual(Version.objects.using("mysql").get_deleted(TestModel).count(), 1)


class GetDeletedModelDbTest(TestBase):

    def testGetDeletedModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        obj.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 0)
        self.assertEqual(Version.objects.get_deleted(TestModel, model_db="postgres").count(), 1)


class FieldDictTest(TestBase):

    def testFieldDict(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v1",
            "related_instances": [],
        })

    def testFieldDictM2M(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
            obj_2 = TestModel.objects.create()
            obj_1.related_instances.add(obj_2)
        self.assertEqual(Version.objects.get_for_object(obj_1).get().field_dict, {
            "id": obj_1.pk,
            "name": "v1",
            "related_instances": [obj_2.pk],
        })

    def testFieldDictFieldFields(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, fields=("name",))
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "name": "v1",
        })

    def testFieldDictFieldExclude(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, exclude=("name",))
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "related_instances": [],
        })


class FieldDictInheritanceTest(TestBase):

    def testFieldDictInheritance(self):
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v1",
            "related_instances": [],
            "parent_name": "parent v1",
            "testmodel_ptr_id": obj.pk,
        })

    def testFieldDictInheritanceUpdate(self):
        obj = TestModelParent.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.parent_name = "parent v2"
            obj.save()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v2",
            "parent_name": "parent v2",
            "related_instances": [],
            "testmodel_ptr_id": obj.pk,
        })


class RevertTest(TestBase):

    def testRevert(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        Version.objects.get_for_object(obj)[1].revert()
        obj.refresh_from_db()
        self.assertEqual(obj.name, "v1")

    def testRevertBadSerializedData(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        Version.objects.get_for_object(obj).update(serialized_data="boom")
        with self.assertRaises(reversion.RevertError):
            Version.objects.get_for_object(obj).get().revert()

    def testRevertBadFormat(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        Version.objects.get_for_object(obj).update(format="boom")
        with self.assertRaises(reversion.RevertError):
            Version.objects.get_for_object(obj).get().revert()


class RevisionRevertTest(TestBase):

    def testRevert(self):
        with reversion.create_revision():
            obj_1 = TestModel.objects.create(
                name="obj_1 v1"
            )
            obj_2 = TestModel.objects.create(
                name="obj_2 v1"
            )
        with reversion.create_revision():
            obj_1.name = "obj_1 v2"
            obj_1.save()
            obj_2.name = "obj_2 v2"
            obj_2.save()
        Version.objects.get_for_object(obj_1)[1].revision.revert()
        obj_1.refresh_from_db()
        self.assertEqual(obj_1.name, "obj_1 v1")
        obj_2.refresh_from_db()
        self.assertEqual(obj_2.name, "obj_2 v1")


class RevisionRevertDeleteTest(TestBase):

    def testRevertDelete(self):
        reversion.unregister(TestModel)
        reversion.register(TestModel, follow=("related_instances",))
        with reversion.create_revision():
            obj_1 = TestModel.objects.create()
        obj_2 = TestModel.objects.create()
        with reversion.create_revision():
            obj_1.related_instances.add(obj_2)
            obj_1.name = "v2"
            obj_1.save()
        Version.objects.get_for_object(obj_1)[1].revision.revert(delete=True)
        obj_1.refresh_from_db()
        self.assertEqual(obj_1.name, "v1")
        self.assertFalse(TestModel.objects.filter(pk=obj_2.pk).exists())
