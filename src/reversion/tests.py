"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

import datetime

from django.db import models
from django.test import TestCase
from django.core.management import call_command

import reversion
from reversion.revisions import RegistrationError
from reversion.models import Revision, Version, VERSION_ADD, VERSION_CHANGE, VERSION_DELETE


class TestModelBase(models.Model):

    name = models.CharField(
        max_length = 100,
    )
    
    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class TestModel1(TestModelBase):

    pass


str_pk_gen = 0;

def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1;
    return str(str_pk_gen)
    
    
class TestModel2(TestModelBase):

    id = models.CharField(
        primary_key = True,
        max_length = 100,
        default = get_str_pk
    )
    
    
class RegistrationTest(TestCase):

    def testRegistration(self):
        # Register the model and test.
        reversion.register(TestModel1)
        self.assertTrue(reversion.is_registered(TestModel1))
        self.assertRaises(RegistrationError, lambda: reversion.register(TestModel1))
        self.assertTrue(TestModel1 in reversion.get_registered_models())
        self.assertTrue(isinstance(reversion.get_adapter(TestModel1), reversion.VersionAdapter))
        # Unregister the model and text.
        reversion.unregister(TestModel1)
        self.assertFalse(reversion.is_registered(TestModel1))
        self.assertRaises(RegistrationError, lambda: reversion.unregister(TestModel1))
        self.assertTrue(TestModel1 not in reversion.get_registered_models())
        self.assertRaises(RegistrationError, lambda: isinstance(reversion.get_adapter(TestModel1)))


class ReversionTestBase(TestCase):

    def setUp(self):
        # Remove all the current registered models.
        self.registered_models = reversion.get_registered_models()
        for model in self.registered_models:
            reversion.unregister(model)
        # Register the test models.
        reversion.register(TestModel1)
        reversion.register(TestModel2)
        # Create some test data.
        self.test11 = TestModel1.objects.create(
            name = "model1 instance1 version1",
        )
        self.test12 = TestModel1.objects.create(
            name = "model1 instance2 version1",
        )
        self.test21 = TestModel2.objects.create(
            name = "model2 instance1 version1",
        )
        self.test22 = TestModel2.objects.create(
            name = "model2 instance2 version1",
        )
        
    def tearDown(self):
         # Re-register the old registered models.
        for model in self.registered_models:
            reversion.register(model)
        # Unregister the test models.
        reversion.unregister(TestModel1)
        reversion.unregister(TestModel2)
        # Delete the test models.
        TestModel1.objects.all().delete()
        TestModel2.objects.all().delete()
        del self.test11
        del self.test12
        del self.test21
        del self.test22
        # Delete the revisions index.
        Revision.objects.all().delete()


class RevisionTestBase(ReversionTestBase):

    @reversion.create_revision
    def setUp(self):
        super(RevisionTestBase, self).setUp()


class InternalsTest(RevisionTestBase):

    def testRevisionsCreated(self):
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testContextManager(self):
        # New revision should be created.
        with reversion.context():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 5)
        
    def testEmptyRevisionNotCreated(self):
        with reversion.context():
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testRevisionContextAbandonedOnError(self):
        try:
            with reversion.context():
                self.test11.name = "model1 instance1 version2"
                self.test11.save()
                raise Exception("Foo")
        except:
            pass
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.count(), 4)
        
    def testRevisionDecoratorAbandonedOnError(self):
        @reversion.create_revision
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
        with reversion.context():
            self.test11.save()
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 4)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 1)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 0)
        with reversion.context():
            self.test11.delete()
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 4)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 1)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 1)


class ApiTest(RevisionTestBase):
    
    def setUp(self):
        super(ApiTest, self).setUp()
        with reversion.context():
            self.test11.name = "model1 instance1 version2"
            self.test11.save()
            self.test12.name = "model1 instance2 version2"
            self.test12.save()
            self.test21.name = "model2 instance1 version2"
            self.test21.save()
            self.test22.name = "model2 instance2 version2"
            self.test22.save()
    
    def testCanGetForObjectReference(self):
        # Test a model with an int pk.
        versions = reversion.get_for_object_reference(TestModel1, self.test11.pk)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[1].field_dict["name"], "model1 instance1 version1")
        # Test a model with a str pk.
        versions = reversion.get_for_object_reference(TestModel2, self.test21.pk)
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
        with reversion.context():
            self.test11.save()
            self.test21.save()
        # Test a model with an int pk.
        self.assertEqual(reversion.get_for_object(self.test11).count(), 3)
        self.assertEqual(len(reversion.get_unique_for_object(self.test11)), 2)
        # Test a model with a str pk.
        self.assertEqual(reversion.get_for_object(self.test21).count(), 3)
        self.assertEqual(len(reversion.get_unique_for_object(self.test21)), 2)
        
    def testCanGetForDate(self):
        now = datetime.datetime.now()
        # Test a model with an int pk.
        version = reversion.get_for_date(self.test11, now)
        self.assertEqual(version.field_dict["name"], "model1 instance1 version2")
        self.assertRaises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test11, datetime.datetime(1970, 1, 1)))
        # Test a model with a str pk.
        version = reversion.get_for_date(self.test21, now)
        self.assertEqual(version.field_dict["name"], "model2 instance1 version2")
        self.assertRaises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test21, datetime.datetime(1970, 1, 1)))
        
    def testCanGetDeleted(self):
        with reversion.context():
            self.test11.delete()
            self.test21.delete()
        # Test a model with an int pk.
        versions = reversion.get_deleted(TestModel1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model1 instance1 version2")
        self.assertEqual(versions[0].type, VERSION_DELETE)
        # Test a model with a str pk.
        versions = reversion.get_deleted(TestModel2)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].field_dict["name"], "model2 instance1 version2")
        self.assertEqual(versions[0].type, VERSION_DELETE)
                
        
class CreateInitialRevisionsTest(ReversionTestBase):

    def testCreateInitialRevisions(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Version.objects.count(), 0)
        call_command("createinitialrevisions")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        call_command("createinitialrevisions")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        
    def testCreateInitialRevisionsSpecificApps(self):
        call_command("createinitialrevisions", "auth")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        
    def testCreateInitialRevisionsSpecificModels(self):
        call_command("createinitialrevisions", "auth.TestModel1")
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.count(), 2)
        call_command("createinitialrevisions", "auth.TestModel2")
        self.assertEqual(Revision.objects.count(), 4)
        self.assertEqual(Version.objects.count(), 4)
        
    def testCreateInitialRevisionsSpecificComment(self):
        call_command("createinitialrevisions", comment="Foo bar")
        self.assertEqual(Revision.objects.all()[0].comment, "Foo bar")


# Import the depricated tests.
from reversion import tests_depricated

for name, value in vars(tests_depricated).iteritems():
    if isinstance(value, type) and issubclass(value, TestCase):
        globals()[name] = value
del name
del value