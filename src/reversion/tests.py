"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

from django.db import models
from django.test import TestCase
from django.core.management import call_command

import reversion
from reversion.revisions import RegistrationError
from reversion.models import Revision, Version


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