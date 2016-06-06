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

    def testRevisionCreatedInRevisionBlock(self):
        with reversion.create_revision():
            obj = TestModel.objects.create()
        self.assertRevisionCreated(obj)

    def testRevisionCreatedInNestedRevisionBlock(self):
        with reversion.create_revision():
            with reversion.create_revision():
                obj = TestModel.objects.create()
        self.assertRevisionCreated(obj)

    def testEmptyRevisionBlockCreatesNoRevision(self):
        with reversion.create_revision():
            pass
        self.assertEqual(Version.objects.count(), 0)

    def testExceptionInRevisionBlockCreatesNoRevision(self):
        try:
            with reversion.create_revision():
                obj = TestModel.objects.create()
                raise Exception("Boom!")
        except:
            pass
        self.assertRevisionNotCreated(obj)

    def testSaveOutsideRevisionBlockCreatesNoRevision(self):
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

    # Multi DB.

    def testRevisionCreatedInMySQL(self):
        with reversion.create_revision(db="mysql"):
            obj = TestModel.objects.create()
        self.assertRevisionCreated(obj, db="mysql")

    def testRevisionCreatedInPostgres(self):
        with reversion.create_revision(db="postgres"):
            obj = TestModel.objects.create()
        self.assertRevisionCreated(obj, db="postgres")

    def testMultipleRevisionsCreatedInMultipleDatabases(self):
        with reversion.create_revision():
            with reversion.create_revision(db="mysql"):
                with reversion.create_revision(db="postgres"):
                    obj = TestModel.objects.create()
        self.assertRevisionCreated(obj)
        self.assertRevisionCreated(obj, db="mysql")
        self.assertRevisionCreated(obj, db="postgres")


class MetadataAPITest(ReversionTestBase):

    def testGetSetComment(self):
        comment = "v1 comment"
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
        meta_name = "meta 1"
        with reversion.create_revision():
<<<<<<< HEAD
            obj = TestModel.objects.create()
            reversion.add_meta(TestMeta, name=meta_name)
        self.assertRevisionCreated(obj, meta_names=(meta_name,))
=======
            proxy.name = "proxy model"
            proxy.save()

        proxy_versions = reversion.get_for_object(proxy)

        self.assertEqual(proxy_versions[0].field_dict["name"], proxy.name)
        self.assertEqual(proxy_versions[1].field_dict["name"], concrete.name)


class FollowModelsTest(ReversionTestBase):

    def setUp(self):
        super(FollowModelsTest, self).setUp()
        reversion.unregister(ReversionTestModel1)
        reversion.register(ReversionTestModel1, follow=("testfollowmodel_set",))
        reversion.register(TestFollowModel, follow=("test_model_1", "test_model_2s",))
        with reversion.create_revision():
            self.follow1 = TestFollowModel.objects.create(
                name="related instance1 version 1",
                test_model_1=self.test11,
            )
            self.follow1.test_model_2s.add(self.test21, self.test22)

    def testRelationsFollowed(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        with reversion.create_revision():
            self.follow1.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 8)

    def testRevertWithDelete(self):
        with reversion.create_revision():
            test23 = ReversionTestModel2.objects.create(
                name="model2 instance3 version1",
            )
            self.follow1.test_model_2s.add(test23)
            self.follow1.save()
        self.assertEqual(reversion.get_for_object(test23).count(), 1)
        self.assertEqual(self.follow1.test_model_2s.all().count(), 3)
        # Test that a revert with delete works.
        test23_pk = test23.pk
        self.assertEqual(ReversionTestModel2.objects.count(), 3)
        with reversion.create_revision():
            reversion.get_for_object(self.follow1)[1].revision.revert(delete=True)
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.count(), 2)
        self.assertRaises(ReversionTestModel2.DoesNotExist, lambda: ReversionTestModel2.objects.get(id=test23_pk))
        # Roll back to the revision where all models were present.
        reversion.get_for_object(self.follow1)[1].revision.revert()
        self.assertEqual(self.follow1.test_model_2s.all().count(), 3)
        # Roll back to a revision where a delete flag is present.
        reversion.get_for_object(self.follow1)[0].revision.revert(delete=True)
        self.assertEqual(self.follow1.test_model_2s.all().count(), 2)

    def testReverseRelationsFollowed(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        with reversion.create_revision():
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 8)

    def testReverseFollowRevertWithDelete(self):
        with reversion.create_revision():
            follow2 = TestFollowModel.objects.create(
                name="related instance2 version 1",
                test_model_1=self.test11,
            )
        # Test that a revert with delete works.
        follow2_pk = follow2.pk
        self.assertEqual(TestFollowModel.objects.count(), 2)
        reversion.get_for_object(self.test11)[1].revision.revert(delete=True)
        self.assertEqual(TestFollowModel.objects.count(), 1)
        self.assertRaises(TestFollowModel.DoesNotExist, lambda: TestFollowModel.objects.get(id=follow2_pk))

    def testRecoverDeleted(self):
        # Delete the test model.
        with reversion.create_revision():
            self.test11.delete()
        self.assertEqual(TestFollowModel.objects.count(), 0)
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        # Recover the test model.
        with reversion.create_revision():
            reversion.get_deleted(ReversionTestModel1)[0].revision.revert()
        # Make sure it was recovered.
        self.assertEqual(TestFollowModel.objects.count(), 1)
        self.assertEqual(ReversionTestModel1.objects.count(), 2)

    def tearDown(self):
        reversion.unregister(TestFollowModel)
        super(FollowModelsTest, self).tearDown()


excluded_revision_manager = reversion.RevisionManager("excluded")


class ExcludedFieldsTest(RevisionTestBase):

    def setUp(self):
        excluded_revision_manager.register(ReversionTestModel1, fields=("id",))
        excluded_revision_manager.register(ReversionTestModel2, exclude=("name",))
        super(ExcludedFieldsTest, self).setUp()

    def testExcludedRevisionManagerIsSeparate(self):
        self.assertEqual(excluded_revision_manager.get_for_object(self.test11).count(), 1)

    def testExcludedFieldsAreRespected(self):
        self.assertEqual(
            excluded_revision_manager.get_for_object(self.test11)[0].field_dict["id"],
            self.test11.id,
        )
        self.assertEqual(excluded_revision_manager.get_for_object(self.test11)[0].field_dict["name"], "")
        self.assertEqual(
            excluded_revision_manager.get_for_object(self.test21)[0].field_dict["id"],
            self.test21.id,
        )
        self.assertEqual(excluded_revision_manager.get_for_object(self.test21)[0].field_dict["name"], "")

    def tearDown(self):
        super(ExcludedFieldsTest, self).tearDown()
        excluded_revision_manager.unregister(ReversionTestModel1)
        excluded_revision_manager.unregister(ReversionTestModel2)


class CreateInitialRevisionsTest(ReversionTestBase):

    def testCreateInitialRevisions(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Version.objects.count(), 0)
        call_command("createinitialrevisions")
        revcount = Revision.objects.count()
        vercount = Version.objects.count()
        self.assertTrue(revcount >= 4)
        self.assertTrue(vercount >= 4)
        call_command("createinitialrevisions")
        self.assertEqual(Revision.objects.count(), revcount)
        self.assertEqual(Version.objects.count(), vercount)

    def testCreateInitialRevisionsSpecificApps(self):
        call_command("createinitialrevisions", "test_app")
        self.assertEqual(Revision.objects.count(), 6)
        self.assertEqual(Version.objects.count(), 6)

    def testCreateInitialRevisionsSpecificModels(self):
        call_command("createinitialrevisions", "test_app.ReversionTestModel1")
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 2)
        call_command("createinitialrevisions", "test_app.ReversionTestModel2")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)

    def testCreateInitialRevisionsSpecificComment(self):
        call_command("createinitialrevisions", comment="Foo bar")
        self.assertEqual(Revision.objects.all()[0].comment, "Foo bar")


class DeleteRevisionsTest(ReversionTestBase):

    def testDeleteRevisions(self):
        call_command("createinitialrevisions")
        self.assertGreater(Version.objects.count(), 4)
        call_command("deleterevisions", "test_app", interactive=False, verbosity=0)
        self.assertEqual(Version.objects.count(), 0)


# Tests for reversion functionality that's tied to requests.
class VersionAdminTest(TestCase):

    def setUp(self):
        self.user = User(
            username="foo",
            is_staff=True,
            is_superuser=True,
        )
        self.user.set_password("bar")
        self.user.save()
        # Log the user in.
        self.client.login(
            username="foo",
            password="bar",
        )

    def tearDown(self):
        self.client.logout()

    def testAutoRegisterWorks(self):
        self.assertTrue(reversion.is_registered(ChildTestAdminModel))
        self.assertTrue(reversion.is_registered(ParentTestAdminModel))
        self.assertTrue(reversion.is_registered(InlineTestChildModel))
        self.assertTrue(reversion.is_registered(InlineTestChildGenericModel))
        self.assertTrue(reversion.is_registered(InlineTestParentModel))

    def testChangelist(self):
        response = self.client.get("/admin/test_app/childtestadminmodel/")
        self.assertEqual(response.status_code, 200)

    def testRevisionSavedOnPost(self):
        self.assertEqual(ChildTestAdminModel.objects.count(), 0)
        # Create an instance via the admin.
        response = self.client.post("/admin/test_app/childtestadminmodel/add/", {
            "parent_name": "parent instance1 version1",
            "child_name": "child instance1 version1",
            "_continue": 1,
        })
        self.assertEqual(response.status_code, 302)
        obj_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        obj = ChildTestAdminModel.objects.get(id=obj_pk)
        # Check that a version is created.
        versions = reversion.get_for_object(obj)
        self.assertEqual(versions.count(), 1)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version1")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version1")
        # Save a new version.
        response = self.client.post(reverse("admin:test_app_childtestadminmodel_change", args=(obj_pk,)), {
            "parent_name": "parent instance1 version2",
            "child_name": "child instance1 version2",
            "_continue": 1,
        })
        self.assertEqual(response.status_code, 302)
        # Check that a version is created.
        versions = reversion.get_for_object(obj)
        self.assertEqual(versions.count(), 2)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version2")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version2")
        # Check that the versions can be listed.
        response = self.client.get(reverse("admin:test_app_childtestadminmodel_history", args=(obj_pk,)))
        self.assertContains(response, "child instance1 version2")
        self.assertContains(response, "child instance1 version1")
        # Check that version data can be loaded.
        response = self.client.get(reverse(
            "admin:test_app_childtestadminmodel_revision",
            args=(obj_pk, versions[1].pk)
        ))
        self.assertContains(response, "parent instance1 version1")
        self.assertContains(response, "child instance1 version1")
        # Check that loading the version data didn't roll it back!
        obj = ChildTestAdminModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.child_name, "child instance1 version2")
        self.assertEqual(obj.parent_name, "parent instance1 version2")
        self.assertEqual(reversion.get_for_object(obj).count(), 2)
        # Check that a version can be rolled back.
        response = self.client.post(
            reverse(
                "admin:test_app_childtestadminmodel_revision",
                args=(obj_pk, versions[1].pk)
            ),
            {
                "parent_name": "parent instance1 version3",
                "child_name": "child instance1 version3",
            },
        )
        self.assertEqual(response.status_code, 302)
        # Check that the models were rolled back.
        obj = ChildTestAdminModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.child_name, "child instance1 version3")
        self.assertEqual(obj.parent_name, "parent instance1 version3")
        # Check that a version is created.
        versions = reversion.get_for_object(obj)
        self.assertEqual(versions.count(), 3)
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version3")
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version3")
        # Check that a deleted version can be viewed in the list.
        obj.delete()
        response = self.client.get("/admin/test_app/childtestadminmodel/recover/")
        self.assertContains(response, "child instance1 version3")
        # Check that a delete version can be viewed in detail.
        response = self.client.get(reverse("admin:test_app_childtestadminmodel_recover", args=(versions[0].pk,)))
        self.assertContains(response, "parent instance1 version3")
        self.assertContains(response, "child instance1 version3")
        # Check that a deleted version can be recovered.
        response = self.client.post(reverse("admin:test_app_childtestadminmodel_recover", args=(versions[0].pk,)), {
            "parent_name": "parent instance1 version4",
            "child_name": "child instance1 version4",
        })
        # Check that the models were rolled back.
        obj = ChildTestAdminModel.objects.get(pk=obj_pk)
        self.assertEqual(obj.child_name, "child instance1 version4")
        self.assertEqual(obj.parent_name, "parent instance1 version4")
        # Check that a version is created.
        versions = reversion.get_for_object_reference(ChildTestAdminModel, obj_pk)
        self.assertEqual(versions.count(), 4)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version4")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version4")

    def createInlineObjects(self):
        # Create an instance via the admin without a child.
        response = self.client.post(reverse("admin:test_app_inlinetestparentmodel_add"), {
            "name": "parent version1",
            "children-TOTAL_FORMS": "0",
            "children-INITIAL_FORMS": "0",
            "test_app-inlinetestchildgenericmodel-content_type-object_id-TOTAL_FORMS": "0",
            "test_app-inlinetestchildgenericmodel-content_type-object_id-INITIAL_FORMS": "0",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        parent_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        parent = InlineTestParentModel.objects.get(id=parent_pk)
        # Update  instance via the admin to add a child
        response = self.client.post(reverse("admin:test_app_inlinetestparentmodel_change", args=(parent_pk,)), {
            "name": "parent version2",
            "children-TOTAL_FORMS": "1",
            "children-INITIAL_FORMS": "0",
            "children-0-name": "non-generic child version 1",
            "test_app-inlinetestchildgenericmodel-content_type-object_id-TOTAL_FORMS": "1",
            "test_app-inlinetestchildgenericmodel-content_type-object_id-INITIAL_FORMS": "0",
            "test_app-inlinetestchildgenericmodel-content_type-object_id-0-name": "generic child version 1",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        children = InlineTestChildModel.objects.filter(parent=parent_pk)
        self.assertEqual(children.count(), 1)
        generic_children = parent.generic_children.all()
        self.assertEqual(generic_children.count(), 1)
        # get list of versions
        version_list = reversion.get_for_object(parent)
        self.assertEqual(len(version_list), 2)
        # All done!
        return parent_pk

    def testInlineAdmin(self):
        self.assertTrue(reversion.is_registered(InlineTestParentModel))
        # make sure model is following the child FK
        self.assertTrue('children' in reversion.get_adapter(InlineTestParentModel).follow)
        parent_pk = self.createInlineObjects()
        # Check that the current version includes the inlines.
        versions = list(reversion.get_for_object_reference(InlineTestParentModel, parent_pk))
        response = self.client.get(reverse(
            "admin:test_app_inlinetestparentmodel_revision",
            args=(parent_pk, versions[0].pk),
        ))
        self.assertContains(response, "parent version2")  # Check parent model.
        self.assertContains(response, "non-generic child version 1")  # Check inline child model.
        self.assertContains(response, "generic child version 1")  # Check inline generic child model.
        # Check that the first version does not include the inlines.
        response = self.client.get(reverse(
            "admin:test_app_inlinetestparentmodel_revision",
            args=(parent_pk, versions[1].pk),
        ))
        self.assertContains(response, "parent version1")  # Check parent model.
        self.assertNotContains(response, "non-generic child version 1")  # Check inline child model.
        self.assertNotContains(response, "generic child version 1")  # Check inline generic child model.

    def createInlineProxyObjects(self):
        # Create an instance via the admin without a child.
        response = self.client.post(reverse("admin:test_app_inlinetestparentmodelproxy_add"), {
            "name": "parent version1",
            "children-TOTAL_FORMS": "0",
            "children-INITIAL_FORMS": "0",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        parent_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        parent = InlineTestParentModelProxy.objects.get(id=parent_pk)
        # Update  instance via the admin to add a child
        response = self.client.post(reverse("admin:test_app_inlinetestparentmodelproxy_change", args=(parent_pk,)), {
            "name": "parent version2",
            "children-TOTAL_FORMS": "1",
            "children-INITIAL_FORMS": "0",
            "children-0-name": "non-generic child version 1",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        children = InlineTestChildModelProxy.objects.filter(parent=parent_pk)
        self.assertEqual(children.count(), 1)
        # get list of versions
        version_list = reversion.get_for_object(parent)
        self.assertEqual(len(version_list), 2)
        # All done!
        return parent_pk

    def testInlineProxyAdmin(self):
        self.assertTrue(reversion.is_registered(InlineTestParentModelProxy))
        # make sure model is following the child FK
        self.assertTrue('children' in reversion.get_adapter(InlineTestParentModelProxy).follow)
        parent_pk = self.createInlineProxyObjects()
        # Check that the current version includes the inlines.
        versions = list(reversion.get_for_object_reference(InlineTestParentModelProxy, parent_pk))
        response = self.client.get(reverse(
            "admin:test_app_inlinetestparentmodelproxy_revision",
            args=(parent_pk, versions[0].pk),
        ))
        self.assertContains(response, "parent version2")  # Check parent model.
        self.assertContains(response, "non-generic child version 1")  # Check inline child model.
        # Check that the first version does not include the inlines.
        response = self.client.get(reverse(
            "admin:test_app_inlinetestparentmodelproxy_revision",
            args=(parent_pk, versions[1].pk),
        ))
        self.assertContains(response, "parent version1")  # Check parent model.
        self.assertNotContains(response, "non-generic child version 1")  # Check inline child model.


# Tests for optional patch generation methods.

try:
    from reversion.helpers import generate_patch, generate_patch_html
except ImportError:  # pragma: no cover
    can_test_patch = False
else:
    can_test_patch = True


class PatchTest(RevisionTestBase):

    def setUp(self):
        super(PatchTest, self).setUp()
        with reversion.create_revision():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.version2, self.version1 = reversion.get_for_object(self.test11)

    @skipUnless(can_test_patch, "Diff match patch library not installed")
    def testCanGeneratePatch(self):
        self.assertEqual(
            generate_patch(self.version1, self.version2, "name"),
            "@@ -17,9 +17,9 @@\n  version\n-1\n+2\n",
        )

    @skipUnless(can_test_patch, "Diff match patch library not installed")
    def testCanGeneratePathHtml(self):
        self.assertEqual(
            generate_patch_html(self.version1, self.version2, "name"),
            (
                '<span>model1 instance1 version</span>'
                '<del style="background:#ffe6e6;">1</del>'
                '<ins style="background:#e6ffe6;">2</ins>'
            ),
        )


# Test Various PK Types
class PrimaryKeyDataTypesTest(TestCase):

    def setUp(self):
        self.table_types = [
            ReversionTestModelPKAutoInt,
            ReversionTestModelPKBigInt,
            ReversionTestModelPKString,
            ReversionTestModelPKGuid,
            ReversionTestModelPKDecimal,
            ReversionTestModelPKFloat
        ]

        for table_type in self.table_types:
            reversion.register(table_type)
>>>>>>> master


<<<<<<< HEAD
class RawRevisionAPITest(ReversionTestBase):

    def testSaveRevision(self):
        obj = TestModel.objects.create()
        reversion.save_revision((obj,))
        self.assertRevisionCreated(obj)
=======
        for table_type in self.table_types:
            self.assertTrue(reversion.is_registered(table_type))
            with reversion.create_revision():
                record = table_type.objects.create(name="Testing")
            versions = reversion.get_for_object(record)
            self.assertEqual(versions.count(), 1)

    def tearDown(self):
        for table_type in self.table_types:
            reversion.unregister(table_type)
>>>>>>> master
