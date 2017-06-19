from django.utils.encoding import force_text
import reversion
from reversion.models import Version
from test_app.models import TestModel, TestModelRelated, TestModelParent
from test_app.tests.base import TestBase, TestModelMixin, TestModelParentMixin


class GetForModelTest(TestModelMixin, TestBase):

    def testGetForModel(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_model(obj.__class__).count(), 1)


class GetForModelDbTest(TestModelMixin, TestBase):

    def testGetForModelDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.using("postgres").get_for_model(obj.__class__).count(), 1)

    def testGetForModelDbMySql(self):
        with reversion.create_revision(using="mysql"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.using("mysql").get_for_model(obj.__class__).count(), 1)


class GetForObjectTest(TestModelMixin, TestBase):

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


class GetForObjectDbTest(TestModelMixin, TestBase):

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


class GetForObjectModelDbTest(TestModelMixin, TestBase):

    def testGetForObjectModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        self.assertEqual(Version.objects.get_for_object(obj).count(), 0)
        self.assertEqual(Version.objects.get_for_object(obj, model_db="postgres").count(), 1)


class GetForObjectUniqueTest(TestModelMixin, TestBase):

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


class GetForObjectReferenceTest(TestModelMixin, TestBase):

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


class GetForObjectReferenceDbTest(TestModelMixin, TestBase):

    def testGetForObjectReferenceModelDb(self):
        with reversion.create_revision(using="postgres"):
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object_reference(TestModel, obj.pk).count(), 0)
        self.assertEqual(Version.objects.using("postgres").get_for_object_reference(TestModel, obj.pk).count(), 1)


class GetForObjectReferenceModelDbTest(TestModelMixin, TestBase):

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


class GetDeletedTest(TestModelMixin, TestBase):

    def testGetDeleted(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        with reversion.create_revision():
            obj.save()
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


class GetDeletedDbTest(TestModelMixin, TestBase):

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


class GetDeletedModelDbTest(TestModelMixin, TestBase):

    def testGetDeletedModelDb(self):
        with reversion.create_revision():
            obj = TestModel.objects.db_manager("postgres").create()
        obj.delete()
        self.assertEqual(Version.objects.get_deleted(TestModel).count(), 0)
        self.assertEqual(Version.objects.get_deleted(TestModel, model_db="postgres").count(), 1)


class FieldDictTest(TestModelMixin, TestBase):

    def testFieldDict(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v1",
            "related": [],
        })

    def testFieldDictM2M(self):
        obj_related = TestModelRelated.objects.create()
        with reversion.create_revision():
            obj = TestModel.objects.create()
            obj.related.add(obj_related)
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v1",
            "related": [obj_related.pk],
        })


class FieldDictFieldsTest(TestBase):

    def testFieldDictFieldFields(self):
        reversion.register(TestModel, fields=("name",))
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "name": "v1",
        })


class FieldDictExcludeTest(TestBase):

    def testFieldDictFieldExclude(self):
        reversion.register(TestModel, exclude=("name",))
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "related": [],
        })


class FieldDictInheritanceTest(TestModelParentMixin, TestBase):

    def testFieldDictInheritance(self):
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        self.assertEqual(Version.objects.get_for_object(obj).get().field_dict, {
            "id": obj.pk,
            "name": "v1",
            "related": [],
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
            "related": [],
            "testmodel_ptr_id": obj.pk,
        })


class M2MTest(TestModelMixin, TestBase):

    def testM2MSave(self):
        v1 = TestModelRelated.objects.create(name="v1")
        v2 = TestModelRelated.objects.create(name="v2")
        with reversion.create_revision():
            obj = TestModel.objects.create()
            obj.related.add(v1)
            obj.related.add(v2)
        version = Version.objects.get_for_object(obj).first()
        self.assertEqual(set(version.field_dict["related"]), set((v1.pk, v2.pk,)))


class RevertTest(TestModelMixin, TestBase):

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


class RevisionRevertTest(TestModelMixin, TestBase):

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
        reversion.register(TestModel, follow=("related",))
        reversion.register(TestModelRelated)
        with reversion.create_revision():
            obj = TestModel.objects.create()
        obj_related = TestModelRelated.objects.create()
        with reversion.create_revision():
            obj.related.add(obj_related)
            obj.name = "v2"
            obj.save()
        Version.objects.get_for_object(obj)[1].revision.revert(delete=True)
        obj.refresh_from_db()
        self.assertEqual(obj.name, "v1")
        self.assertFalse(TestModelRelated.objects.filter(pk=obj_related.pk).exists())
