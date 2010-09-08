"""
Doctests for Reversion.

These tests require Python version 2.5 or higher to run.
"""


from __future__ import with_statement

import datetime

from django.db import models, transaction
from django.test import TestCase

import reversion
from reversion.models import Version, Revision
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
        
        
class ReversionCustomRegistrationTest(TestCase):
    
    """Tests the custom model registration options."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Register the model.
        reversion.register(TestModel, fields=("id",), format="xml")
        # Create some initial revisions.
        with reversion.revision:
            self.test = TestModel.objects.create(name="test1.0")
        with reversion.revision:
            self.test.name = "test1.1"
            self.test.save()
        with reversion.revision:
            self.test.name = "test1.2"
            self.test.save()
            
    def testCustomRegistrationHonored(self):
        """Ensures that the custom settings were honored."""
        self.assertEqual(reversion.revision.get_registration_info(TestModel).fields, ("id",))
        self.assertEqual(reversion.revision.get_registration_info(TestModel).format, "xml")
        
    def testCanRevertOnlySpecifiedFields(self):
        """"Ensures that only the restricted set of fields are loaded."""
        Version.objects.get_for_object(self.test)[0].revert()
        self.assertEqual(TestModel.objects.get().name, "")
            
    def testCustomSerializationFormat(self):
        """Ensures that the custom serialization format is used."""
        self.assertEquals(Version.objects.get_for_object(self.test)[0].serialized_data[0], "<");
            
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(TestModel)
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        # Clear references.
        del self.test
        
        
class TestRelatedModel(models.Model):
    
    """A model used to test Reversion relation following."""
    
    name = models.CharField(max_length=100)
    
    relation = models.ForeignKey(TestModel)
    
    class Meta:
        app_label = "reversion"
        
        
class ReversionRelatedTest(TestCase):
    
    """Tests the ForeignKey and OneToMany support."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        TestRelatedModel.objects.all().delete()
        # Register the models.
        reversion.register(TestModel, follow=("testrelatedmodel_set",))
        reversion.register(TestRelatedModel, follow=("relation",))
    
    def testCanCreateRevisionForiegnKey(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        self.assertEqual(Version.objects.get_for_object(related).count(), 1)
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.get_for_object(test)[0].revision.version_set.all().count(), 2)
        
    def testCanCreateRevisionOneToMany(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.save()
        self.assertEqual(Version.objects.get_for_object(test).count(), 2)
        self.assertEqual(Version.objects.get_for_object(related).count(), 2)
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.get_for_object(test)[1].revision.version_set.all().count(), 2)
    
    def testCanRevertRevision(self):
        """Tests that an entire revision can be reverted."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.name = "test1.1"
            test.save()
            related.name = "related1.1"
            related.save()
        # Attempt revert.
        Version.objects.get_for_object(test)[0].revision.revert()
        self.assertEqual(TestModel.objects.get().name, "test1.0")
        self.assertEqual(TestRelatedModel.objects.get().name, "related1.0")
        
    def testCanRecoverRevision(self):
        """Tests that an entire revision can be recovered."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.name = "test1.1"
            test.save()
            related.name = "related1.1"
            related.save()
        # Delete the models.
        test.delete()
        # Ensure deleted.
        self.assertEqual(TestModel.objects.count(), 0)
        self.assertEqual(TestRelatedModel.objects.count(), 0)
        # Query the deleted models..
        self.assertEqual(len(Version.objects.get_deleted(TestModel)), 1)
        self.assertEqual(len(Version.objects.get_deleted(TestRelatedModel)), 1)
        # Revert the revision.
        Version.objects.get_deleted(TestModel)[0].revision.revert()
        # Ensure reverted.
        self.assertEqual(TestModel.objects.count(), 1)
        self.assertEqual(TestRelatedModel.objects.count(), 1)
        # Ensure correct version.
        self.assertEqual(TestModel.objects.get().name, "test1.1")
        self.assertEqual(TestRelatedModel.objects.get().name, "related1.1")
    
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the models.
        reversion.unregister(TestModel)
        reversion.unregister(TestRelatedModel)
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        TestRelatedModel.objects.all().delete()


class TestManyToManyModel(models.Model):
    
    """A model used to test Reversion M2M relation following."""
    
    name = models.CharField(max_length=100)
    
    relations = models.ManyToManyField(TestModel)
    
    class Meta:
        app_label = "reversion"
        
        
class ReversionManyToManyTest(TestCase):
    
    """Tests the ManyToMany support."""
    
    def setUp(self):
        """Sets up the TestModel."""
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        TestManyToManyModel.objects.all().delete()
        # Register the models.
        reversion.register(TestModel, follow=("testmanytomanymodel_set",))
        reversion.register(TestManyToManyModel, follow=("relations",))
    
    def testCanCreateRevision(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test1 = TestModel.objects.create(name="test1.0")
            test2 = TestModel.objects.create(name="test2.0")
            related = TestManyToManyModel.objects.create(name="related1.0")
            related.relations.add(test1)
            related.relations.add(test2)
        self.assertEqual(Version.objects.get_for_object(test1).count(), 1)
        self.assertEqual(Version.objects.get_for_object(test2).count(), 1)
        self.assertEqual(Version.objects.get_for_object(related).count(), 1)
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.get_for_object(related)[0].revision.version_set.all().count(), 3)
        
    def testCanCreateRevisionRelated(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test = TestModel.objects.create(name="test1.0")
            related1 = TestManyToManyModel.objects.create(name="related1.0")
            related2 = TestManyToManyModel.objects.create(name="related2.0")
            test.testmanytomanymodel_set.add(related1)
            test.testmanytomanymodel_set.add(related2)
        with reversion.revision:
            test.save()
        self.assertEqual(Version.objects.get_for_object(test).count(), 2)
        self.assertEqual(Version.objects.get_for_object(related1).count(), 2)
        self.assertEqual(Version.objects.get_for_object(related2).count(), 2)
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(Version.objects.get_for_object(test)[0].revision.version_set.all().count(), 3)
    
    def testCanRevertRevision(self):
        """Tests that an entire revision can be reverted."""
        with reversion.revision:
            test1 = TestModel.objects.create(name="test1.0")
            test2 = TestModel.objects.create(name="test2.0")
            related = TestManyToManyModel.objects.create(name="related1.0")
            related.relations.add(test1)
            related.relations.add(test2)
        with reversion.revision:
            test1.name = "test1.1"
            test1.save()
            test2.name = "test2.1"
            test2.save()
            related.name = "related1.1"
            related.save()
        # Attempt revert.
        Version.objects.get_for_object(related)[0].revision.revert()
        self.assertEqual(TestModel.objects.get(pk=test1.pk).name, "test1.0")
        self.assertEqual(TestModel.objects.get(pk=test2.pk).name, "test2.0")
        self.assertEqual(TestManyToManyModel.objects.get().name, "related1.0")
        
    def testCanRecoverRevision(self):
        """Tests that an entire revision can be recovered."""
        with reversion.revision:
            test1 = TestModel.objects.create(name="test1.0")
            test2 = TestModel.objects.create(name="test2.0")
            related = TestManyToManyModel.objects.create(name="related1.0")
            related.relations.add(test1)
            related.relations.add(test2)
        with reversion.revision:
            test1.name = "test1.1"
            test1.save()
            test2.name = "test2.1"
            test2.save()
            related.name = "related1.1"
            related.save()
        # Save the pks.
        test1_pk = test1.pk
        test2_pk = test2.pk
        # Delete the models.
        related.delete()
        test1.delete()
        test2.delete()
        # Ensure deleted.
        self.assertEqual(TestModel.objects.count(), 0)
        self.assertEqual(TestManyToManyModel.objects.count(), 0)
        # Query the deleted models..
        self.assertEqual(len(Version.objects.get_deleted(TestModel)), 2)
        self.assertEqual(len(Version.objects.get_deleted(TestManyToManyModel)), 1)
        # Revert the revision.
        Version.objects.get_deleted(TestManyToManyModel)[0].revision.revert()
        # Ensure reverted.
        self.assertEqual(TestModel.objects.count(), 2)
        self.assertEqual(TestManyToManyModel.objects.count(), 1)
        # Ensure correct version.
        self.assertEqual(TestModel.objects.get(pk=test1_pk).name, "test1.1")
        self.assertEqual(TestModel.objects.get(pk=test2_pk).name, "test2.1")
        self.assertEqual(TestManyToManyModel.objects.get().name, "related1.1")
    
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the models.
        reversion.unregister(TestModel)
        reversion.unregister(TestManyToManyModel)
        # Clear the database.
        Version.objects.all().delete()
        TestModel.objects.all().delete()
        TestManyToManyModel.objects.all().delete()


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
            
            