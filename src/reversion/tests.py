"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

from __future__ import with_statement

import datetime, os

from django.db import models
from django.test import TestCase
from django.core.management import call_command
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.decorators import decorator_from_middleware
from django.http import HttpResponse
from django.utils.unittest import skipUnless

import reversion
from reversion.revisions import RegistrationError, RevisionManager
from reversion.models import Revision, Version, VERSION_ADD, VERSION_CHANGE, VERSION_DELETE
from reversion.middleware import RevisionMiddleware


ZERO = datetime.timedelta(0)


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

class ReversionTestModelBase(models.Model):

    name = models.CharField(
        max_length = 100,
    )
    
    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class ReversionTestModel1(ReversionTestModelBase):

    pass


str_pk_gen = 0;

def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1;
    return str(str_pk_gen)
    
    
class ReversionTestModel2(ReversionTestModelBase):

    id = models.CharField(
        primary_key = True,
        max_length = 100,
        default = get_str_pk
    )
    
    
class ReversionTestModel1Proxy(ReversionTestModel1):

    class Meta:
        proxy = True
        
        
class RevisionMeta(models.Model):

    revision = models.OneToOneField(Revision)

    age = models.IntegerField()
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
    
    
class RegistrationTest(TestCase):

    def testRegistration(self):
        # Register the model and test.
        reversion.register(ReversionTestModel1)
        self.assertTrue(reversion.is_registered(ReversionTestModel1))
        self.assertRaises(RegistrationError, lambda: reversion.register(ReversionTestModel1))
        self.assertTrue(ReversionTestModel1 in reversion.get_registered_models())
        self.assertTrue(isinstance(reversion.get_adapter(ReversionTestModel1), reversion.VersionAdapter))
        # Unregister the model and text.
        reversion.unregister(ReversionTestModel1)
        self.assertFalse(reversion.is_registered(ReversionTestModel1))
        self.assertRaises(RegistrationError, lambda: reversion.unregister(ReversionTestModel1))
        self.assertTrue(ReversionTestModel1 not in reversion.get_registered_models())
        self.assertRaises(RegistrationError, lambda: isinstance(reversion.get_adapter(ReversionTestModel1)))
        
    def testProxyRegistration(self):
        # Test error if registering proxy models.
        self.assertRaises(RegistrationError, lambda: reversion.register(ReversionTestModel1Proxy))


class ReversionTestBase(TestCase):

    def setUp(self):
        # Unregister all registered models.
        self.initial_registered_models = []
        for registered_model in reversion.get_registered_models():
            self.initial_registered_models.append((registered_model, reversion.get_adapter(registered_model).__class__))
            reversion.unregister(registered_model)
        # Register the test models.
        reversion.register(ReversionTestModel1)
        reversion.register(ReversionTestModel2)
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
        self.user = User.objects.create(
            username = "user1",
        )
        
    def tearDown(self):
        # Unregister the test models.
        reversion.unregister(ReversionTestModel1)
        reversion.unregister(ReversionTestModel2)
        # Delete the test models.
        ReversionTestModel1.objects.all().delete()
        ReversionTestModel2.objects.all().delete()
        User.objects.all().delete()
        del self.test11
        del self.test12
        del self.test21
        del self.test22
        del self.user
        # Delete the revisions index.
        Revision.objects.all().delete()
        # Unregister all remaining models.
        for registered_model in reversion.get_registered_models():
            reversion.unregister(registered_model)
        # Re-register initial registered models.
        for initial_model, adapter in self.initial_registered_models:
            reversion.register(initial_model, adapter_cls=adapter)
        del self.initial_registered_models


class RevisionTestBase(ReversionTestBase):

    @reversion.create_revision()
    def setUp(self):
        super(RevisionTestBase, self).setUp()


class InternalsTest(RevisionTestBase):

    def testRevisionsCreated(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testContextManager(self):
        # New revision should be created.
        with reversion.create_revision():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)
    
    def testManualRevisionManagement(self):
        # When manage manually is on, no revisions created.
        with reversion.create_revision(manage_manually=True):
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        # Save a manual revision.
        reversion.default_revision_manager.save_revision([self.test11])
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)
        
    def testEmptyRevisionNotCreated(self):
        with reversion.create_revision():
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testRevisionContextAbandonedOnError(self):
        try:
            with reversion.create_revision():
                self.test11.name = "model1 instance1 version2"
                self.test11.save()
                raise Exception("Foo")
        except:
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testRevisionDecoratorAbandonedOnError(self):
        @reversion.create_revision()
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
        
    def testCorrectVersionFlags(self):
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 4)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 0)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 0)
        with reversion.create_revision():
            self.test11.save()
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 4)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 1)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 0)
        with reversion.create_revision():
            self.test11.delete()
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 4)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 1)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 1)


class ApiTest(RevisionTestBase):
    
    def setUp(self):
        super(ApiTest, self).setUp()
        with reversion.create_revision():
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
        reversion.pre_revision_commit.connect(pre_revision_receiver)
        reversion.post_revision_commit.connect(post_revision_receiver)
        # Create a revision.
        with reversion.create_revision():
            self.test11.save()
        # Check the signals were called.
        self.assertTrue(pre_revision_receiver_called)
        self.assertTrue(post_revision_receiver_called)
    
    def testCanGetForObjectReference(self):
        # Test a model with an int pk.
        versions = reversion.get_for_object_reference(ReversionTestModel1, self.test11.pk)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model1 instance1 version1")
        # Test a model with a str pk.
        versions = reversion.get_for_object_reference(ReversionTestModel2, self.test21.pk)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model2 instance1 version1")
    
    def testCanGetForObject(self):
        # Test a model with an int pk.
        versions = reversion.get_for_object(self.test11)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model1 instance1 version1")
        # Test a model with a str pk.
        versions = reversion.get_for_object(self.test21)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model2 instance1 version1")
        
    def testCanGetUniqueForObject(self):
        with reversion.create_revision():
            self.test11.save()
            self.test21.save()
        # Test a model with an int pk.
        self.assertEqual(reversion.get_for_object(self.test11).count(), 3)
        self.assertEqual(len(reversion.get_unique_for_object(self.test11)), 2)
        # Test a model with a str pk.
        self.assertEqual(reversion.get_for_object(self.test21).count(), 3)
        self.assertEqual(len(reversion.get_unique_for_object(self.test21)), 2)
        
    def testCanGetForDate(self):
        with self.settings(USE_TZ=True):
            now = datetime.datetime.now(UTC())
            # Test a model with an int pk.
            version = reversion.get_for_date(self.test11, now)
            self.assertEqual(version.field_dict["name"], "model1 instance1 version2")
            self.assertRaises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test11, datetime.datetime(1970, 1, 1, tzinfo=UTC())))
            # Test a model with a str pk.
            version = reversion.get_for_date(self.test21, now)
            self.assertEqual(version.field_dict["name"], "model2 instance1 version2")
            self.assertRaises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test21, datetime.datetime(1970, 1, 1, tzinfo=UTC())))
        
    def testCanGetDeleted(self):
        with reversion.create_revision():
            self.test11.delete()
            self.test21.delete()
        # Test a model with an int pk.
        versions = reversion.get_deleted(ReversionTestModel1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        # Test a model with a str pk.
        versions = reversion.get_deleted(ReversionTestModel2)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        
    def testCanRevertVersion(self):
        reversion.get_for_object(self.test11)[1].revert()
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")
        
    def testCanRevertRevision(self):
        reversion.get_for_object(self.test11)[1].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.pk).name, "model1 instance1 version1")
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test12.pk).name, "model1 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test22.pk).name, "model2 instance2 version1")
    
    def testCanRevertRevisionWithDeletedVersions(self):
        self.assertEqual(ReversionTestModel1.objects.count(), 2)
        self.assertEqual(ReversionTestModel2.objects.count(), 2)
        with reversion.create_revision():
            self.test11.name = "model1 instance1 version3"
            self.test11.save()
            self.test12.delete()
            self.test21.name = "model2 instance1 version3"
            self.test21.save()
            self.test22.delete()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        with reversion.create_revision():
            self.test11.name = "model1 instance1 version4"
            self.test11.save()
            self.test21.name = "model2 instance1 version4"
            self.test21.save()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        # Revert to a revision where some deletes were logged.
        reversion.get_for_object(self.test11)[1].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.count(), 1)
        self.assertEqual(ReversionTestModel2.objects.count(), 1)
        self.assertEqual(ReversionTestModel1.objects.get(id=self.test11.id).name, "model1 instance1 version3")
        self.assertEqual(ReversionTestModel2.objects.get(id=self.test21.id).name, "model2 instance1 version3")
        # Revert the a revision before the deletes were logged.
        reversion.get_for_object(self.test11)[2].revision.revert()
        self.assertEqual(ReversionTestModel1.objects.count(), 2)
        self.assertEqual(ReversionTestModel2.objects.count(), 2)
    
    def testCanSaveIgnoringDuplicates(self):
        with reversion.create_revision():
            self.test11.save()
            self.test12.save()
            self.test21.save()
            self.test22.save()
            self.assertFalse(reversion.get_ignore_duplicates())
            reversion.set_ignore_duplicates(True)
            self.assertTrue(reversion.get_ignore_duplicates())
        self.assertEqual(reversion.get_for_object(self.test11).count(), 2)
        # Save a non-duplicate revision.
        with reversion.create_revision():
            self.test11.save()
            self.assertFalse(reversion.get_ignore_duplicates())
            reversion.set_ignore_duplicates(True)
        self.assertEqual(reversion.get_for_object(self.test11).count(), 3)
        
    def testCanAddMetaToRevision(self):
        # Create a revision with lots of meta data.
        with reversion.create_revision():
            self.test11.save()
            reversion.set_comment("Foo bar")
            self.assertEqual(reversion.get_comment(), "Foo bar")
            reversion.set_user(self.user)
            self.assertEqual(reversion.get_user(), self.user)
            reversion.add_meta(RevisionMeta, age=5)
        # Test the revision data.
        revision = reversion.get_for_object(self.test11)[0].revision
        self.assertEqual(revision.user, self.user)
        self.assertEqual(revision.comment, "Foo bar")
        self.assertEqual(revision.revisionmeta.age, 5)


class ReversionTestModel1Child(ReversionTestModel1):

    pass
    
    
class MultiTableInheritanceApiTest(RevisionTestBase):

    def setUp(self):
        super(MultiTableInheritanceApiTest, self).setUp()
        reversion.register(ReversionTestModel1Child, follow=("reversiontestmodel1_ptr",))
        with reversion.create_revision():
            self.testchild1 = ReversionTestModel1Child.objects.create(
                name = "modelchild1 instance1 version 1",
            )
    
    def testCanRetreiveFullFieldDict(self):
        self.assertEqual(reversion.get_for_object(self.testchild1)[0].field_dict["name"], "modelchild1 instance1 version 1")
    
    def tearDown(self):
        super(MultiTableInheritanceApiTest, self).tearDown()
        del self.testchild1


class TestFollowModel(ReversionTestModelBase):

    test_model_1 = models.ForeignKey(
        ReversionTestModel1,
    )
    
    test_model_2s = models.ManyToManyField(
        ReversionTestModel2,
    )
    
    
class FollowModelsTest(ReversionTestBase):

    @reversion.create_revision()
    def setUp(self):
        super(FollowModelsTest, self).setUp()
        reversion.unregister(ReversionTestModel1)
        reversion.register(ReversionTestModel1, follow=("testfollowmodel_set",))
        reversion.register(TestFollowModel, follow=("test_model_1", "test_model_2s",))
        self.follow1 = TestFollowModel.objects.create(
            name = "related instance1 version 1",
            test_model_1 = self.test11,
        )
        self.follow1.test_model_2s.add(self.test21, self.test22)
    
    def testRelationsFollowed(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 5)
        with reversion.create_revision():
            self.follow1.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 9)
    
    def testRevertWithDelete(self):
        with reversion.create_revision():
            test23 = ReversionTestModel2.objects.create(
                name = "model2 instance3 version1",
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
        self.assertEqual(Version.objects.count(), 5)
        with reversion.create_revision():
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 9)
    
    def testReverseFollowRevertWithDelete(self):
        with reversion.create_revision():
            follow2 = TestFollowModel.objects.create(
                name = "related instance2 version 1",
                test_model_1 = self.test11,
            )
        # Test that a revert with delete works.
        follow2_pk = follow2.pk
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
        TestFollowModel.objects.all().delete()
        del self.follow1
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
        call_command("createinitialrevisions", "auth")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        
    def testCreateInitialRevisionsSpecificModels(self):
        call_command("createinitialrevisions", "auth.ReversionTestModel1")
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 2)
        call_command("createinitialrevisions", "auth.ReversionTestModel2")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        
    def testCreateInitialRevisionsSpecificComment(self):
        call_command("createinitialrevisions", comment="Foo bar")
        self.assertEqual(Revision.objects.all()[0].comment, "Foo bar")


# Tests for reversion functionality that's tied to requests.        

revision_middleware_decorator = decorator_from_middleware(RevisionMiddleware)

# A dumb view that saves a revision.
@revision_middleware_decorator
def save_revision_view(request):
    ReversionTestModel1.objects.create(
        name = "model1 instance3 version1",
    )
    ReversionTestModel1.objects.create(
        name = "model1 instance4 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance3 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance4 version1",
    )
    return HttpResponse("OK")
    
    
# A dumb view that borks a revision.
@revision_middleware_decorator
def error_revision_view(request):
    ReversionTestModel1.objects.create(
        name = "model1 instance3 version1",
    )
    ReversionTestModel1.objects.create(
        name = "model1 instance4 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance3 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance4 version1",
    )
    raise Exception("Foo")


site = admin.AdminSite()


class ParentTestAdminModel(models.Model):

    parent_name = models.CharField(
        max_length = 200,
    )
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520


class ChildTestAdminModel(ParentTestAdminModel):

    child_name = models.CharField(
        max_length = 200,
    )
    
    def __unicode__(self):
        return self.child_name
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520


class ChildTestAdminModelAdmin(reversion.VersionAdmin):

    pass
    
    
site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


urlpatterns = patterns("",

    url("^success/$", save_revision_view),
    
    url("^error/$", error_revision_view),
    
    url("^admin/", include(site.get_urls(), namespace="admin")),

)


class RevisionMiddlewareTest(ReversionTestBase):

    urls = "reversion.tests"

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


class VersionAdminTest(TestCase):

    urls = "reversion.tests"

    def setUp(self):
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(admin.__file__), "templates"),
        )
        self.user = User(
            username = "foo",
            is_staff = True,
            is_superuser = True,
        )
        self.user.set_password("bar")
        self.user.save()
        # Log the user in.
        if hasattr(self, "settings"):
            with self.settings(INSTALLED_APPS=tuple(set(tuple(settings.INSTALLED_APPS) + ("django.contrib.sessions",)))):  # HACK: Without this the client won't log in, for some reason.
                self.client.login(
                    username = "foo",
                    password = "bar",
                )
        else:
            self.client.login(
                username = "foo",
                password = "bar",
            )

    @skipUnless('django.contrib.admin' in settings.INSTALLED_APPS,
                "django.contrib.admin not activated")
    def testAutoRegisterWorks(self):
        self.assertTrue(reversion.is_registered(ChildTestAdminModel))
        self.assertTrue(reversion.is_registered(ParentTestAdminModel))

    @skipUnless('django.contrib.admin' in settings.INSTALLED_APPS,
                "django.contrib.admin not activated")
    def testRevisionSavedOnPost(self):
        self.assertEqual(ChildTestAdminModel.objects.count(), 0)
        # Create an instance via the admin.
        response = self.client.post("/admin/auth/childtestadminmodel/add/", {
            "parent_name": "parent instance1 version1",
            "child_name": "child instance1 version1",
            "_continue": 1,
        })
        self.assertEqual(response.status_code, 302)
        obj_pk = response["Location"].split("/")[-2]
        obj = ChildTestAdminModel.objects.get(id=obj_pk)
        # Check that a version is created.
        versions = reversion.get_for_object(obj)
        self.assertEqual(versions.count(), 1)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version1")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version1")
        # Save a new version.
        response = self.client.post("/admin/auth/childtestadminmodel/%s/" % obj_pk, {
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
        response = self.client.get("/admin/auth/childtestadminmodel/%s/history/" % obj_pk)
        self.assertContains(response, "child instance1 version2")
        self.assertContains(response, "child instance1 version1")
        # Check that a version can be rolled back.
        response = self.client.post("/admin/auth/childtestadminmodel/%s/history/%s/" % (obj_pk, versions[1].pk), {
            "parent_name": "parent instance1 version3",
            "child_name": "child instance1 version3",
        })
        self.assertEqual(response.status_code, 302)
        # Check that a version is created.
        versions = reversion.get_for_object(obj)
        self.assertEqual(versions.count(), 3)
        self.assertEqual(versions[0].field_dict["parent_name"], "parent instance1 version3")
        self.assertEqual(versions[0].field_dict["child_name"], "child instance1 version3")
        # Check that a deleted version can be viewed.
        obj.delete()
        response = self.client.get("/admin/auth/childtestadminmodel/recover/")
        self.assertContains(response, "child instance1 version3")
        # Check that a deleted version can be recovered.
        response = self.client.post("/admin/auth/childtestadminmodel/recover/%s/" % versions[0].pk, {
            "parent_name": "parent instance1 version4",
            "child_name": "child instance1 version4",
        })
        obj = ChildTestAdminModel.objects.get(id=obj_pk)
        
    def tearDown(self):
        self.client.logout()
        self.user.delete()
        del self.user
        ChildTestAdminModel.objects.all().delete()
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS


# Tests for optional patch generation methods.

try:
    from reversion.helpers import generate_patch, generate_patch_html
except ImportError:
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
            u'<span>model1 instance1 version</span><del style="background:#ffe6e6;">1</del><ins style="background:#e6ffe6;">2</ins>',
        )
                         
    def tearDown(self):
        super(PatchTest, self).tearDown()
        del self.version1
        del self.version2


# Import the deprecated tests.
from reversion import tests_deprecated

for name, value in vars(tests_deprecated).iteritems():
    if isinstance(value, type) and issubclass(value, TestCase):
        globals()[name] = value
del name
del value
