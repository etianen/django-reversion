"""
Tests for the django-reversion API.
"""

from __future__ import unicode_literals

import datetime, os
from unittest import skipUnless

from django.db import models
from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_delete
from django.utils import timezone
from django.core.urlresolvers import reverse, resolve

from reversion.revisions import (
    register,
    unregister,
    is_registered,
    get_registered_models,
    get_adapter,
    VersionAdapter,
    default_revision_manager,
    create_revision,
    get_for_object_reference,
    get_for_object,
    get_unique_for_object,
    get_for_date,
    get_ignore_duplicates,
    set_ignore_duplicates,
    get_deleted,
    set_comment,
    get_comment,
    set_user,
    get_user,
    add_meta,
    RevisionManager,
)
from reversion.models import Revision, Version
from reversion.errors import RegistrationError
from reversion.signals import pre_revision_commit, post_revision_commit

from test_reversion.models import (
    ReversionTestModel1,
    ReversionTestModel1Child,
    ReversionTestModel2,
    ReversionTestModel3,
    TestFollowModel,
    ReversionTestModel1Proxy,
    RevisionMeta,
    ParentTestAdminModel,
    ChildTestAdminModel,
    InlineTestParentModel,
    InlineTestParentModelProxy,
    InlineTestChildModel,
    InlineTestChildGenericModel,
    InlineTestChildModelProxy,
)
from test_reversion import admin  # Force early registration of all admin models.

User = get_user_model()

ZERO = datetime.timedelta(0)


class RegistrationTest(TestCase):

    def check_registration(self, test_model):
        # Register the model and test.
        register(test_model)
        self.assertTrue(is_registered(test_model))
        self.assertRaises(RegistrationError, lambda: register(test_model))
        self.assertTrue(test_model in get_registered_models())
        self.assertTrue(isinstance(get_adapter(test_model), VersionAdapter))

    def check_deregistration(self, test_model):
        # Unregister the model and text.
        unregister(test_model)
        self.assertFalse(is_registered(test_model))
        self.assertRaises(RegistrationError, lambda: unregister(test_model))
        self.assertTrue(test_model not in get_registered_models())
        self.assertRaises(RegistrationError, lambda: isinstance(get_adapter(test_model)))

    def testRegistration(self):
        self.check_registration(ReversionTestModel1)
        self.check_deregistration(ReversionTestModel1)

    def testProxyRegistration(self):
        # ProxyModel registered as usual model
        self.check_registration(ReversionTestModel1Proxy)
        self.check_deregistration(ReversionTestModel1Proxy)

    def testDecorator(self):
        # Test the use of register as a decorator
        @register
        class DecoratorModel(models.Model):
            pass
        self.assertTrue(is_registered(DecoratorModel))

    def testDecoratorArgs(self):
        # Test a decorator with arguments
        @register(format='yaml')
        class DecoratorArgsModel(models.Model):
            pass
        self.assertTrue(is_registered(DecoratorArgsModel))

    def testEagerRegistration(self):
        # Register the model and test.
        register(ReversionTestModel3, eager_signals=[pre_delete])
        self.assertTrue(is_registered(ReversionTestModel3))
        self.assertRaises(RegistrationError, lambda: register(ReversionTestModel3, eager_signals=[pre_delete]))
        self.assertTrue(ReversionTestModel3 in get_registered_models())
        self.assertTrue(isinstance(get_adapter(ReversionTestModel3), VersionAdapter))
        self.assertEqual([], default_revision_manager._signals[ReversionTestModel3])
        self.assertEqual([pre_delete], default_revision_manager._eager_signals[ReversionTestModel3])
        # Unregister the model and text.
        unregister(ReversionTestModel3)
        self.assertFalse(is_registered(ReversionTestModel3))
        self.assertRaises(RegistrationError, lambda: unregister(ReversionTestModel3))
        self.assertTrue(ReversionTestModel3 not in get_registered_models())
        self.assertRaises(RegistrationError, lambda: isinstance(get_adapter(ReversionTestModel3)))
        self.assertFalse(ReversionTestModel3 in default_revision_manager._signals)
        self.assertFalse(ReversionTestModel3 in default_revision_manager._eager_signals)


class ReversionTestBase(TestCase):

    def setUp(self):
        # Unregister all registered models.
        self.initial_registered_models = []
        for registered_model in get_registered_models():
            self.initial_registered_models.append((registered_model, get_adapter(registered_model).__class__))
            unregister(registered_model)
        # Register the test models.
        register(ReversionTestModel1)
        register(ReversionTestModel2)
        register(ReversionTestModel3, eager_signals=[pre_delete])
        # Create some test data.
        self.test11 = ReversionTestModel1.objects.create(
            name = "model1 instance1 version1",
        )
        self.test12 = ReversionTestModel1.objects.create(
            name = "model1 instance2 version1",
        )
        self.test21 = ReversionTestModel2.objects.create(
            name = "model2 instance1 version1",
        )
        self.test22 = ReversionTestModel2.objects.create(
            name = "model2 instance2 version1",
        )
        self.test31 = ReversionTestModel3.objects.create(
            name = "model3 instance1 version1",
        )
        self.test32 = ReversionTestModel3.objects.create(
            name = "model3 instance2 version1",
        )
        self.user = User.objects.create(
            username = "user1",
        )

    def tearDown(self):
        # Unregister the test models.
        unregister(ReversionTestModel1)
        unregister(ReversionTestModel2)
        unregister(ReversionTestModel3)
        # Unregister all remaining models.
        for registered_model in get_registered_models():
            unregister(registered_model)
        # Re-register initial registered models.
        for initial_model, adapter in self.initial_registered_models:
            register(initial_model, adapter_cls=adapter)
        del self.initial_registered_models


class RevisionTestBase(ReversionTestBase):

    @create_revision()
    def setUp(self):
        super(RevisionTestBase, self).setUp()


class InternalsTest(RevisionTestBase):

    def testRevisionsCreated(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)

    def testContextManager(self):
        # New revision should be created.
        with create_revision():
            with create_revision():
                self.test11.name = "model1 instance1 version2"
                self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)

    def testManualRevisionManagement(self):
        # When manage manually is on, no revisions created.
        with create_revision(manage_manually=True):
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        # Save a manual revision.
        default_revision_manager.save_revision([self.test11])
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)

    def testEmptyRevisionNotCreated(self):
        with create_revision():
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)

    def testRevisionContextAbandonedOnError(self):
        with create_revision():
            try:
                with create_revision():
                    self.test11.name = "model1 instance1 version2"
                    self.test11.save()
                    raise Exception("Foo")
            except:
                pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)

    def testRevisionDecoratorAbandonedOnError(self):
        @create_revision()
        def make_revision():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
            raise Exception("Foo")
        try:
            make_revision()
        except:
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)

    def testRevisionCreatedOnDelete(self):
        with create_revision():
            self.test31.delete()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)

    def testNoVersionForObjectCreatedAndDeleted(self):
        with create_revision():
            new_object = ReversionTestModel1.objects.create()
            new_object.delete()
        # No Revision and no Version should have been created.
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)


class ApiTest(RevisionTestBase):

    def setUp(self):
        super(ApiTest, self).setUp()
        with create_revision():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
            self.test12.name = "model1 instance2 version2"
            self.test12.save()
            self.test21.name = "model2 instance1 version2"
            self.test21.save()
            self.test22.name = "model2 instance2 version2"
            self.test22.save()

    def testRevisionSignals(self):
        pre_revision_receiver_called = []

        def pre_revision_receiver(**kwargs):
            self.assertEqual(kwargs["instances"], [self.test11])
            self.assertTrue(isinstance(kwargs["revision"], Revision))
            self.assertEqual(len(kwargs["versions"]), 1)
            pre_revision_receiver_called.append(True)
        post_revision_receiver_called = []

        def post_revision_receiver(**kwargs):
            self.assertEqual(kwargs["instances"], [self.test11])
            self.assertTrue(isinstance(kwargs["revision"], Revision))
            self.assertEqual(len(kwargs["versions"]), 1)
            post_revision_receiver_called.append(True)
        pre_revision_commit.connect(pre_revision_receiver)
        post_revision_commit.connect(post_revision_receiver)
        # Create a revision.
        with create_revision():
            self.test11.save()
        # Check the signals were called.
        self.assertTrue(pre_revision_receiver_called)
        self.assertTrue(post_revision_receiver_called)

    def testCanGetForObjectReference(self):
        # Test a model with an int pk.
        versions = get_for_object_reference(ReversionTestModel1, self.test11.pk)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model1 instance1 version1")
        # Test a model with a str pk.
        versions = get_for_object_reference(ReversionTestModel2, self.test21.pk)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model2 instance1 version1")

    def testCanGetForObject(self):
        # Test a model with an int pk.
        versions = get_for_object(self.test11)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model1 instance1 version1")
        # Test a model with a str pk.
        versions = get_for_object(self.test21)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model2 instance1 version1")

    def testCanGetUniqueForObject(self):
        with create_revision():
            self.test11.save()
            self.test21.save()
        # Test a model with an int pk.
        self.assertEqual(get_for_object(self.test11).count(), 3)
        self.assertEqual(len(get_unique_for_object(self.test11)), 2)
        # Test a model with a str pk.
        self.assertEqual(get_for_object(self.test21).count(), 3)
        self.assertEqual(len(get_unique_for_object(self.test21)), 2)

    def testCanGetUnique(self):
        with create_revision():
            self.test11.save()
            self.test21.save()
        # Test a model with an int pk.
        self.assertEqual(get_for_object(self.test11).count(), 3)
        self.assertEqual(len(list(get_for_object(self.test11).get_unique())), 2)
        # Test a model with a str pk.
        self.assertEqual(get_for_object(self.test21).count(), 3)
        self.assertEqual(len(list(get_for_object(self.test21).get_unique())), 2)

    def testCanGetForDate(self):
        now = timezone.now()
        # Test a model with an int pk.
        version = get_for_date(self.test11, now)
        self.assertEqual(version.field_dict["name"], "model1 instance1 version2")
        self.assertRaises(Version.DoesNotExist, lambda: get_for_date(self.test11, datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)))
        # Test a model with a str pk.
        version = get_for_date(self.test21, now)
        self.assertEqual(version.field_dict["name"], "model2 instance1 version2")
        self.assertRaises(Version.DoesNotExist, lambda: get_for_date(self.test21, datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)))

    def testCanGetDeleted(self):
        with create_revision():
            self.test11.delete()
            self.test21.delete()
        # Test a model with an int pk.
        versions = get_deleted(ReversionTestModel1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        # Test a model with a str pk.
        versions = get_deleted(ReversionTestModel2)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")

    def testCanRevertVersion(self):
        get_for_object(self.test11)[1].revert()
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")

    def testCanRevertRevision(self):
        get_for_object(self.test11)[1].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test12.pk).name, "model1 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")

    def testCanRevertRevisionWithDeletedVersions(self):
        self.assertEqual(ReversionTestModel1.objects.count(), 2)
        self.assertEqual(ReversionTestModel2.objects.count(), 2)
        with create_revision():
            self.test11.name = "model1 instance1 version3"
            self.test11.save()
            self.test12.delete()
            self.test21.name = "model2 instance1 version3"
            self.test21.save()
            self.test22.delete()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        with create_revision():
            self.test11.name = "model1 instance1 version4"
            self.test11.save()
            self.test21.name = "model2 instance1 version4"
            self.test21.save()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        # Revert to a revision where some deletes were logged.
        get_for_object(self.test11)[1].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.id).name, "model1 instance1 version3")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test21.id).name, "model2 instance1 version3")
        # Revert the a revision before the deletes were logged.
        get_for_object(self.test11)[2].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.count(), 2)
        self.assertEqual(ReversionTestModel2.objects.count(), 2)

    def testCanSaveIgnoringDuplicates(self):
        with create_revision():
            self.test11.save()
            self.test12.save()
            self.test21.save()
            self.test22.save()
            self.assertFalse(get_ignore_duplicates())
            set_ignore_duplicates(True)
            self.assertTrue(get_ignore_duplicates())
        self.assertEqual(get_for_object(self.test11).count(), 2)
        # Save a non-duplicate revision.
        with create_revision():
            self.test11.save()
            self.assertFalse(get_ignore_duplicates())
            set_ignore_duplicates(True)
        self.assertEqual(get_for_object(self.test11).count(), 3)

    def testCanAddMetaToRevision(self):
        # Create a revision with lots of meta data.
        with create_revision():
            self.test11.save()
            set_comment("Foo bar")
            self.assertEqual(get_comment(), "Foo bar")
            set_user(self.user)
            self.assertEqual(get_user(), self.user)
            add_meta(RevisionMeta, age=5)
        # Test the revision data.
        revision = get_for_object(self.test11)[0].revision
        self.assertEqual(revision.user, self.user)
        self.assertEqual(revision.comment, "Foo bar")
        self.assertEqual(revision.revisionmeta.age, 5)


class MultiTableInheritanceApiTest(RevisionTestBase):

    def setUp(self):
        super(MultiTableInheritanceApiTest, self).setUp()
        register(ReversionTestModel1Child, follow=("reversiontestmodel1_ptr",))
        with create_revision():
            self.testchild1 = ReversionTestModel1Child.objects.create(
                name = "modelchild1 instance1 version 1",
            )

    def testCanRetreiveFullFieldDict(self):
        self.assertEqual(get_for_object(self.testchild1)[0].field_dict["name"], "modelchild1 instance1 version 1")


class ReversionTestModel1ChildProxy(ReversionTestModel1Child):
    class Meta:
        proxy = True


class ProxyModelApiTest(RevisionTestBase):

    def setUp(self):
        super(ProxyModelApiTest, self).setUp()
        register(ReversionTestModel1Proxy)
        self.concrete = self.test11
        self.proxy = ReversionTestModel1Proxy.objects.get(pk=self.concrete.pk)

        with create_revision():
            self.proxy.name = "proxy model"
            self.proxy.save()

    def testCanGetForObjectReference(self):
        # Can get version for proxy model
        proxy_versions = get_for_object_reference(ReversionTestModel1Proxy, self.proxy.id)
        self.assertEqual(len(proxy_versions), 2)
        self.assertEqual(proxy_versions[0].field_dict["name"], self.proxy.name)
        self.assertEqual(proxy_versions[1].field_dict["name"], self.concrete.name)

        # Can get the same version for concrete model
        concrete_versions = get_for_object_reference(ReversionTestModel1, self.concrete.id)
        self.assertEqual(list(concrete_versions), list(proxy_versions))

    def testCanGetForObject(self):
        # Can get version for proxy model
        proxy_versions = get_for_object(self.proxy)
        self.assertEqual(len(proxy_versions), 2)
        self.assertEqual(proxy_versions[0].field_dict["name"], self.proxy.name)
        self.assertEqual(proxy_versions[1].field_dict["name"], self.concrete.name)

        # Can get the same version for concrete model
        concrete_versions = get_for_object(self.concrete)
        self.assertEqual(list(concrete_versions), list(proxy_versions))

    def testCanRevertVersion(self):
        self.assertEqual(ReversionTestModel1.objects.get(pk=self.concrete.pk).name, self.proxy.name)
        get_for_object(self.proxy)[1].revert()
        self.assertEqual(ReversionTestModel1.objects.get(pk=self.concrete.pk).name, self.concrete.name)

    def testMultiTableInheritanceProxyModel(self):
        register(ReversionTestModel1Child, follow=("reversiontestmodel1_ptr",))
        register(ReversionTestModel1ChildProxy, follow=("reversiontestmodel1_ptr",))

        with create_revision():
            concrete = ReversionTestModel1Child.objects.create(name="modelchild1 instance1 version 1")

        proxy = ReversionTestModel1ChildProxy.objects.get(pk=concrete.pk)
        with create_revision():
            proxy.name = "proxy model"
            proxy.save()

        proxy_versions = get_for_object(proxy)

        self.assertEqual(proxy_versions[0].field_dict["name"], proxy.name)
        self.assertEqual(proxy_versions[1].field_dict["name"], concrete.name)


class FollowModelsTest(ReversionTestBase):

    @create_revision()
    def setUp(self):
        super(FollowModelsTest, self).setUp()
        unregister(ReversionTestModel1)
        register(ReversionTestModel1, follow=("testfollowmodel_set",))
        register(TestFollowModel, follow=("test_model_1", "test_model_2s",))
        self.follow1 = TestFollowModel.objects.create(
            name = "related instance1 version 1",
            test_model_1 = self.test11,
        )
        self.follow1.test_model_2s.add(self.test21, self.test22)

    def testRelationsFollowed(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 5)
        with create_revision():
            self.follow1.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 9)

    def testRevertWithDelete(self):
        with create_revision():
            test23 = ReversionTestModel2.objects.create(
                name = "model2 instance3 version1",
            )
            self.follow1.test_model_2s.add(test23)
            self.follow1.save()
        self.assertEqual(get_for_object(test23).count(), 1)
        self.assertEqual(self.follow1.test_model_2s.all().count(), 3)
        # Test that a revert with delete works.
        test23_pk = test23.pk
        self.assertEqual(ReversionTestModel2.objects.count(), 3)
        with create_revision():
            get_for_object(self.follow1)[1].revision.revert(delete=True)
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.count(), 2)
        self.assertRaises(ReversionTestModel2.DoesNotExist, lambda: ReversionTestModel2.objects.get(id=test23_pk))
        # Roll back to the revision where all models were present.
        get_for_object(self.follow1)[1].revision.revert()
        self.assertEqual(self.follow1.test_model_2s.all().count(), 3)
        # Roll back to a revision where a delete flag is present.
        get_for_object(self.follow1)[0].revision.revert(delete=True)
        self.assertEqual(self.follow1.test_model_2s.all().count(), 2)

    def testReverseRelationsFollowed(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 5)
        with create_revision():
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 9)

    def testReverseFollowRevertWithDelete(self):
        with create_revision():
            follow2 = TestFollowModel.objects.create(
                name = "related instance2 version 1",
                test_model_1 = self.test11,
            )
        # Test that a revert with delete works.
        follow2_pk = follow2.pk
        get_for_object(self.test11)[1].revision.revert(delete=True)
        self.assertEqual(TestFollowModel.objects.count(), 1)
        self.assertRaises(TestFollowModel.DoesNotExist, lambda: TestFollowModel.objects.get(id=follow2_pk))

    def testRecoverDeleted(self):
        # Delete the test model.
        with create_revision():
            self.test11.delete()
        self.assertEqual(TestFollowModel.objects.count(), 0)
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        # Recover the test model.
        with create_revision():
            get_deleted(ReversionTestModel1)[0].revision.revert()
        # Make sure it was recovered.
        self.assertEqual(TestFollowModel.objects.count(), 1)
        self.assertEqual(ReversionTestModel1.objects.count(), 2)

    def tearDown(self):
        unregister(TestFollowModel)
        super(FollowModelsTest, self).tearDown()


excluded_revision_manager = RevisionManager("excluded")


class ExcludedFieldsTest(RevisionTestBase):

    def setUp(self):
        excluded_revision_manager.register(ReversionTestModel1, fields=("id",))
        excluded_revision_manager.register(ReversionTestModel2, exclude=("name",))
        super(ExcludedFieldsTest, self).setUp()

    def testExcludedRevisionManagerIsSeparate(self):
        self.assertEqual(excluded_revision_manager.get_for_object(self.test11).count(), 1)

    def testExcludedFieldsAreRespected(self):
        self.assertEqual(excluded_revision_manager.get_for_object(self.test11)[0].field_dict["id"], self.test11.id)
        self.assertEqual(excluded_revision_manager.get_for_object(self.test11)[0].field_dict["name"], "")
        self.assertEqual(excluded_revision_manager.get_for_object(self.test21)[0].field_dict["id"], self.test21.id)
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
        call_command("createinitialrevisions", "test_reversion")
        self.assertEqual(Revision.objects.count(), 6)
        self.assertEqual(Version.objects.count(), 6)

    def testCreateInitialRevisionsSpecificModels(self):
        call_command("createinitialrevisions", "test_reversion.ReversionTestModel1")
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 2)
        call_command("createinitialrevisions", "test_reversion.ReversionTestModel2")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)

    def testCreateInitialRevisionsSpecificComment(self):
        call_command("createinitialrevisions", comment="Foo bar")
        self.assertEqual(Revision.objects.all()[0].comment, "Foo bar")


class DeleteRevisionsTest(ReversionTestBase):

    def testDeleteRevisions(self):
        call_command("createinitialrevisions")
        self.assertGreater(Version.objects.count(), 4)
        call_command("deleterevisions", "test_reversion", confirmation=False, verbosity=0)
        self.assertEqual(Version.objects.count(), 0)


# Tests for reversion functionality that's tied to requests.

class RevisionMiddlewareTest(ReversionTestBase):

    def testRevisionMiddleware(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Version.objects.count(), 0)
        self.client.get("/success/")
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)

    def testRevisionMiddlewareInvalidatesRevisionOnError(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Version.objects.count(), 0)
        self.assertRaises(Exception, lambda: self.client.get("/error/"))
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Version.objects.count(), 0)

    def testRevisionMiddlewareErrorOnDoubleMiddleware(self):
        self.assertRaises(ImproperlyConfigured, lambda: self.client.get("/double/"))


class VersionAdminTest(TestCase):

    def setUp(self):
        self.user = User(
            username = "foo",
            is_staff = True,
            is_superuser = True,
        )
        self.user.set_password("bar")
        self.user.save()
        # Log the user in.
        self.client.login(
            username = "foo",
            password = "bar",
        )

    def tearDown(self):
        self.client.logout()

    def testAutoRegisterWorks(self):
        self.assertTrue(is_registered(ChildTestAdminModel))
        self.assertTrue(is_registered(ParentTestAdminModel))
        self.assertTrue(is_registered(InlineTestChildModel))
        self.assertTrue(is_registered(InlineTestChildGenericModel))
        self.assertTrue(is_registered(InlineTestParentModel))

    def testChangelist(self):
        response = self.client.get("/admin/test_reversion/childtestadminmodel/")
        self.assertEqual(response.status_code, 200)

    def testRevisionSavedOnPost(self):
        self.assertEqual(ChildTestAdminModel.objects.count(), 0)
        # Create an instance via the admin.
        response = self.client.post("/admin/test_reversion/childtestadminmodel/add/", {
            "parent_name": "parent instance1 version1",
            "child_name": "child instance1 version1",
            "_continue": 1,
        })
        self.assertEqual(response.status_code, 302)
        obj_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        obj = ChildTestAdminModel.objects.get(id=obj_pk)
        # Check that a version is created.
        versions = get_for_object(obj)
        self.assertEqual(versions.count(), 1)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version1")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version1")
        # Save a new version.
        response = self.client.post(reverse("admin:test_reversion_childtestadminmodel_change", args=(obj_pk,)), {
            "parent_name": "parent instance1 version2",
            "child_name": "child instance1 version2",
            "_continue": 1,
        })
        self.assertEqual(response.status_code, 302)
        # Check that a version is created.
        versions = get_for_object(obj)
        self.assertEqual(versions.count(), 2)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version2")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version2")
        # Check that the versions can be listed.
        response = self.client.get(reverse("admin:test_reversion_childtestadminmodel_history", args=(obj_pk,)))
        self.assertContains(response, "child instance1 version2")
        self.assertContains(response, "child instance1 version1")
        # Check that version data can be loaded.
        response = self.client.get(reverse("admin:test_reversion_childtestadminmodel_revision", args=(obj_pk, versions[1].pk)))
        self.assertContains(response, "parent instance1 version1")
        self.assertContains(response, "child instance1 version1")
        # Check that loading the version data didn't roll it back!
        obj = ChildTestAdminModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.child_name, "child instance1 version2")
        self.assertEqual(obj.parent_name, "parent instance1 version2")
        self.assertEqual(get_for_object(obj).count(), 2)
        # Check that a version can be rolled back.
        response = self.client.post(reverse("admin:test_reversion_childtestadminmodel_revision", args=(obj_pk, versions[1].pk)), {
            "parent_name": "parent instance1 version3",
            "child_name": "child instance1 version3",
        })
        self.assertEqual(response.status_code, 302)
        # Check that the models were rolled back.
        obj = ChildTestAdminModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.child_name, "child instance1 version3")
        self.assertEqual(obj.parent_name, "parent instance1 version3")
        # Check that a version is created.
        versions = get_for_object(obj)
        self.assertEqual(versions.count(), 3)
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version3")
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version3")
        # Check that a deleted version can be viewed in the list.
        obj.delete()
        response = self.client.get("/admin/test_reversion/childtestadminmodel/recover/")
        self.assertContains(response, "child instance1 version3")
        # Check that a delete version can be viewed in detail.
        response = self.client.get(reverse("admin:test_reversion_childtestadminmodel_recover", args=(versions[0].pk,)))
        self.assertContains(response, "parent instance1 version3")
        self.assertContains(response, "child instance1 version3")
        # Check that a deleted version can be recovered.
        response = self.client.post(reverse("admin:test_reversion_childtestadminmodel_recover", args=(versions[0].pk,)), {
            "parent_name": "parent instance1 version4",
            "child_name": "child instance1 version4",
        })
        # Check that the models were rolled back.
        obj = ChildTestAdminModel.objects.get(pk=obj_pk)
        self.assertEqual(obj.child_name, "child instance1 version4")
        self.assertEqual(obj.parent_name, "parent instance1 version4")
        # Check that a version is created.
        versions = get_for_object_reference(ChildTestAdminModel, obj_pk)
        self.assertEqual(versions.count(), 4)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version4")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version4")

    def createInlineObjects(self):
        # Create an instance via the admin without a child.
        response = self.client.post(reverse("admin:test_reversion_inlinetestparentmodel_add"), {
            "name": "parent version1",
            "children-TOTAL_FORMS": "0",
            "children-INITIAL_FORMS": "0",
            "test_reversion-inlinetestchildgenericmodel-content_type-object_id-TOTAL_FORMS": "0",
            "test_reversion-inlinetestchildgenericmodel-content_type-object_id-INITIAL_FORMS": "0",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        parent_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        parent = InlineTestParentModel.objects.get(id=parent_pk)
        # Update  instance via the admin to add a child
        response = self.client.post(reverse("admin:test_reversion_inlinetestparentmodel_change", args=(parent_pk,)), {
            "name": "parent version2",
            "children-TOTAL_FORMS": "1",
            "children-INITIAL_FORMS": "0",
            "children-0-name": "non-generic child version 1",
            "test_reversion-inlinetestchildgenericmodel-content_type-object_id-TOTAL_FORMS": "1",
            "test_reversion-inlinetestchildgenericmodel-content_type-object_id-INITIAL_FORMS": "0",
            "test_reversion-inlinetestchildgenericmodel-content_type-object_id-0-name": "generic child version 1",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        children = InlineTestChildModel.objects.filter(parent=parent_pk)
        self.assertEqual(children.count(), 1)
        generic_children = parent.generic_children.all()
        self.assertEqual(generic_children.count(), 1)
        # get list of versions
        version_list = get_for_object(parent)
        self.assertEqual(len(version_list), 2)
        # All done!
        return parent_pk

    def testInlineAdmin(self):
        self.assertTrue(is_registered(InlineTestParentModel))
        # make sure model is following the child FK
        self.assertTrue('children' in get_adapter(InlineTestParentModel).follow)
        parent_pk = self.createInlineObjects()
        # Check that the current version includes the inlines.
        versions = list(get_for_object_reference(InlineTestParentModel, parent_pk))
        response = self.client.get(reverse("admin:test_reversion_inlinetestparentmodel_revision", args=(parent_pk, versions[0].pk)))
        self.assertContains(response, "parent version2")  # Check parent model.
        self.assertContains(response, "non-generic child version 1")  # Check inline child model.
        self.assertContains(response, "generic child version 1")  # Check inline generic child model.
        # Check that the first version does not include the inlines.
        response = self.client.get(reverse("admin:test_reversion_inlinetestparentmodel_revision", args=(parent_pk, versions[1].pk)))
        self.assertContains(response, "parent version1")  # Check parent model.
        self.assertNotContains(response, "non-generic child version 1")  # Check inline child model.
        self.assertNotContains(response, "generic child version 1")  # Check inline generic child model.

    def createInlineProxyObjects(self):
        # Create an instance via the admin without a child.
        response = self.client.post(reverse("admin:test_reversion_inlinetestparentmodelproxy_add"), {
            "name": "parent version1",
            "children-TOTAL_FORMS": "0",
            "children-INITIAL_FORMS": "0",
            "_continue": 1,
            })
        self.assertEqual(response.status_code, 302)
        parent_pk = resolve(response["Location"].replace("http://testserver", "")).args[0]
        parent = InlineTestParentModelProxy.objects.get(id=parent_pk)
        # Update  instance via the admin to add a child
        response = self.client.post(reverse("admin:test_reversion_inlinetestparentmodelproxy_change", args=(parent_pk,)), {
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
        version_list = get_for_object(parent)
        self.assertEqual(len(version_list), 2)
        # All done!
        return parent_pk

    def testInlineProxyAdmin(self):
        self.assertTrue(is_registered(InlineTestParentModelProxy))
        # make sure model is following the child FK
        self.assertTrue('children' in get_adapter(InlineTestParentModelProxy).follow)
        parent_pk = self.createInlineProxyObjects()
        # Check that the current version includes the inlines.
        versions = list(get_for_object_reference(InlineTestParentModelProxy, parent_pk))
        response = self.client.get(reverse("admin:test_reversion_inlinetestparentmodelproxy_revision", args=(parent_pk, versions[0].pk)))
        self.assertContains(response, "parent version2")  # Check parent model.
        self.assertContains(response, "non-generic child version 1")  # Check inline child model.
        # Check that the first version does not include the inlines.
        response = self.client.get(reverse("admin:test_reversion_inlinetestparentmodelproxy_revision", args=(parent_pk, versions[1].pk)))
        self.assertContains(response, "parent version1")  # Check parent model.
        self.assertNotContains(response, "non-generic child version 1")  # Check inline child model.


# Tests for optional patch generation methods.

try:
    from helpers import generate_patch, generate_patch_html
except ImportError:  # pragma: no cover
    can_test_patch = False
else:
    can_test_patch = True


class PatchTest(RevisionTestBase):

    def setUp(self):
        super(PatchTest, self).setUp()
        with create_revision():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.version2, self.version1 = get_for_object(self.test11)

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
            '<span>model1 instance1 version</span><del style="background:#ffe6e6;">1</del><ins style="background:#e6ffe6;">2</ins>',
        )


# test preserve deleted User Revisions
class DeleteUserTest(RevisionTestBase):

    def testDeleteUser(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        rev = Revision.objects.all()[0]
        rev.user = self.user
        rev.save()
        self.user.delete()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
