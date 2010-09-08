"""
Doctests for Reversion.

These tests require Python version 2.5 or higher to run.
"""


from __future__ import with_statement

import datetime

from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models, transaction
from django.test import TestCase

import reversion
from reversion.admin import VersionAdmin
from reversion.helpers import patch_admin
from reversion.models import Version, Revision
from reversion.revisions import RegistrationError, DEFAULT_SERIALIZATION_FORMAT


class TestModel(models.Model):
    
    """A test model for reversion."""
    
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = "reversion"
        
        
class ReversionTest(TestCase):
    
    """Tests the core django-reversion functionality."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Register the model.
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
            
            