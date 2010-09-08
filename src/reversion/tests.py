"""
Doctests for Reversion.

These tests require Python version 2.5 or higher to run.
"""


from __future__ import with_statement

import datetime

from django.db import models, transaction
from django.test import TestCase

import reversion
from reversion.models import Version
from reversion.revisions import RegistrationError, DEFAULT_SERIALIZATION_FORMAT


class TestModel(models.Model):
    
    """A test model for reversion."""
    
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = "reversion"
        
        
class ReversionRegistrationTest(TestCase):
    
    """Tests the django-reversion registration functionality."""
    
    def setUp(self):
        """Sets up the TestModel."""
        reversion.register(TestModel)
        
    def testCanRegisterModel(self):
        """Tests that a model can be registered."""
        self.assertTrue(reversion.is_registered(TestModel))
        # Check that duplicate registration is disallowed.
        self.assertRaises(RegistrationError, lambda: reversion.register(TestModel))
        
    def testCanReadRegistrationInfo(self):
        """Tests that the registration info for a model is obtainable."""
        registration_info = reversion.revision.get_registration_info(TestModel)
        self.assertEqual(registration_info.fields, ("id", "name",))
        self.assertEqual(registration_info.file_fields, ())
        self.assertEqual(registration_info.follow, ())
        self.assertEqual(registration_info.format, DEFAULT_SERIALIZATION_FORMAT)
        
    def testCanUnregisterModel(self):
        """Tests that a model can be unregistered."""
        reversion.unregister(TestModel)
        self.assertFalse(reversion.is_registered(TestModel))
        # Check that duplicate unregistration is disallowed.
        self.assertRaises(RegistrationError, lambda: reversion.unregister(TestModel))
        # Re-register the model.
        reversion.register(TestModel)
        
    def tearDown(self):
        """Tears down the tests."""
        reversion.unregister(TestModel)
        
        
class ReversionCreateTest(TestCase):
    
    """Tests the django-reversion revision creation functionality."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Register the model.
        reversion.register(TestModel)
        
    def testCanSaveWithNoRevision(self):
        """Tests that without an active revision, no model is saved."""
        test = TestModel.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(test).count(), 0)
        
    def testRevisionContextManager(self):
        """Tests that the revision context manager works."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        
    def testRevisionDecorator(self):
        """Tests that the revision function decorator works."""
        @reversion.revision.create_on_success
        def create_revision():
            return TestModel.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(create_revision()).count(), 1)
        
    def testRevisionAbandonedOnError(self):
        """Tests that the revision is abandoned on error."""
        # Create the first revision.
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
        # Create the second revision.
        try:
            with reversion.revision:
                test.name = None
                test.save()
        except:
            transaction.rollback()
        # Check that there is still only one revision.
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(TestModel)
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        
        
class ReversionQueryTest(TestCase):
    
    """Tests that django-reversion can retrieve revisions using the api."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Register the model.
        reversion.register(TestModel)
        # Create some initial revisions.
        with reversion.revision:
            self.test = TestModel.objects.create(name="test1.0")
        with reversion.revision:
            self.test.name = "test1.1"
            self.test.save()
        with reversion.revision:
            self.test.name = "test1.2"
            self.test.save()
            
    def testCanGetVersions(self):
        """Tests that the versions for an obj can be retrieved."""
        versions = Version.objects.get_for_object(self.test)
        self.assertEqual(versions[0].field_dict["name"], "test1.0")
        self.assertEqual(versions[1].field_dict["name"], "test1.1")
        self.assertEqual(versions[2].field_dict["name"], "test1.2")
        
    def testCanGetUniqueVersions(self):
        """Tests that the unique versions for an objext can be retrieved."""
        with reversion.revision:
            self.test.save()
        versions = Version.objects.get_unique_for_object(self.test)
        # Check correct version data.
        self.assertEqual(versions[0].field_dict["name"], "test1.0")
        self.assertEqual(versions[1].field_dict["name"], "test1.1")
        self.assertEqual(versions[2].field_dict["name"], "test1.2")
        # Check correct number of versions.
        self.assertEqual(len(versions), 3)
        
    def testCanGetForDate(self):
        """Tests that the latest version for a particular date can be loaded."""
        self.assertEqual(Version.objects.get_for_date(self.test, datetime.datetime.now()).field_dict["name"], "test1.2")
    
    def testCanRevert(self):
        """Tests that an object can be reverted to a previous revision."""
        oldest = Version.objects.get_for_object(self.test)[0]
        self.assertEqual(oldest.field_dict["name"], "test1.0")
        oldest.revert()
        self.assertEqual(TestModel.objects.get().name, "test1.0")
        
    def testCanGetDeleted(self):
        """Tests that deleted objects can be retrieved."""
        self.assertEqual(len(Version.objects.get_deleted(TestModel)), 0)
        # Delete the test model.
        self.test.delete()
        # Ensure that there is now a deleted model.
        deleted = Version.objects.get_deleted(TestModel)
        self.assertEqual(deleted[0].field_dict["name"], "test1.2")
        self.assertEqual(len(deleted), 1)
        
    def testCanRecoverDeleted(self):
        """Tests that a deleted object can be recovered."""
        self.test.delete()
        # Ensure deleted.
        self.assertEqual(TestModel.objects.count(), 0)
        # Recover.
        Version.objects.get_deleted(TestModel)[0].revert()
        # Ensure recovered.
        self.assertEqual(TestModel.objects.get().name, "test1.2")
        
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(TestModel)
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Clear references.
        del self.test


# Test the patch helpers, if available.

try:
    from reversion.helpers import generate_patch, generate_patch_html
except ImportError:
    pass
else:
    
    class PatchTest(TestCase):
        
        """Tests the patch generation functionality."""
        
        def setUp(self):
            """Sets up a versioned site model to test."""
            # Clear the database.
            Version.objects.all().delete()
            TestModel.objects.all().delete()
            # Register the TestModel.
            reversion.register(TestModel)
            # Create some versions.
            with reversion.revision:
                test = TestModel.objects.create(name="test1.0",)
            with reversion.revision:
                test.name = "test1.1"
                test.save()
            # Get the version data.
            self.test_0 = Version.objects.get_for_object(test)[0]
            self.test_1 = Version.objects.get_for_object(test)[1]
        
        def testCanGeneratePatch(self):
            """Tests that text patches can be generated."""
            self.assertEqual(generate_patch(self.test_0, self.test_1, "name"),
                             "@@ -3,5 +3,5 @@\n st1.\n-0\n+1\n")
        
        def testCanGeneratePathHtml(self):
            """Tests that html patches can be generated."""
            self.assertEqual(generate_patch_html(self.test_0, self.test_1, "name"),
                             u'<SPAN TITLE="i=0">test1.</SPAN><DEL STYLE="background:#FFE6E6;" TITLE="i=6">0</DEL><INS STYLE="background:#E6FFE6;" TITLE="i=6">1</INS>')
        
        def tearDown(self):
            """Deletes the versioned site model."""
            # Unregister the model.
            reversion.unregister(TestModel)
            # Clear the database.
            Version.objects.all().delete()
            TestModel.objects.all().delete()
            # Clear references.
            del self.test_0
            del self.test_1
            
            