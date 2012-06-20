"""Tests for the deprecated version of the django-reversion API."""

from __future__ import with_statement

import datetime

from django.db import models, transaction
from django.test import TestCase
from django.core.management import call_command

import reversion
from reversion.models import Version, Revision, VERSION_ADD, VERSION_CHANGE, VERSION_DELETE
from reversion.revisions import RegistrationError
from reversion.tests import UTC

class ReversionTestModel(models.Model):
    
    """A test model for reversion."""
    
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520


str_pk_gen = 0;

def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1;
    return str(str_pk_gen)
        
        
class ReversionTestModelStrPrimary(models.Model):
    
    """A test model for reversion."""
    
    id = models.CharField(
        primary_key = True,
        max_length = 100,
        default = get_str_pk
    )
    
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class ReversionRegistrationTest(TestCase):
    
    """Tests the django-reversion registration functionality."""
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        reversion.register(ReversionTestModel)
        
    def testCanRegisterModel(self):
        """Tests that a model can be registered."""
        self.assertTrue(reversion.is_registered(ReversionTestModel))
        # Check that duplicate registration is disallowed.
        self.assertRaises(RegistrationError, lambda: reversion.register(ReversionTestModel))
        
    def testCanUnregisterModel(self):
        """Tests that a model can be unregistered."""
        reversion.unregister(ReversionTestModel)
        try:
            self.assertFalse(reversion.is_registered(ReversionTestModel))
            # Check that duplicate unregistration is disallowed.
            self.assertRaises(RegistrationError, lambda: reversion.unregister(ReversionTestModel))
        finally:
            # Re-register the model.
            reversion.register(ReversionTestModel)
        
    def tearDown(self):
        """Tears down the tests."""
        reversion.unregister(ReversionTestModel)
        
        
class ReversionCreateTest(TestCase):
    
    """Tests the django-reversion revision creation functionality."""
    
    model = ReversionTestModel
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        # Register the model.
        reversion.register(self.model)
        
    def testCanSaveWithNoRevision(self):
        """Tests that without an active revision, no model is saved."""
        test = self.model.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(test).count(), 0)
        
    def testRevisionContextManager(self):
        """Tests that the revision context manager works."""
        with reversion.revision:
            test = self.model.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        
    def testRevisionDecorator(self):
        """Tests that the revision function decorator works."""
        @reversion.revision.create_on_success
        def create_revision():
            return self.model.objects.create(name="test1.0")
        self.assertEqual(Version.objects.get_for_object(create_revision()).count(), 1)
        
    def testRevisionAbandonedOnError(self):
        """Tests that the revision is abandoned on error."""
        # Create the first revision.
        with reversion.revision:
            test = self.model.objects.create(name="test1.0")
        # Create the second revision.
        try:
            with reversion.revision:
                test.name = "test1.1"
                test.save()
                raise Exception()
        except:
            transaction.rollback()
        # Check that there is still only one revision.
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        # Assert the revision is not invalid.
        self.assertFalse(reversion.revision._revision_context_manager.is_invalid())
        
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(self.model)
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        
        
class ReversionCreateStrPrimaryTest(ReversionCreateTest):

    model = ReversionTestModelStrPrimary
        
        
class ReversionQueryTest(TestCase):
    
    """Tests that django-reversion can retrieve revisions using the api."""
    
    model = ReversionTestModel
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        # Register the model.
        reversion.register(self.model)
        # Create some initial revisions.
        with reversion.revision:
            self.test = self.model.objects.create(name="test1.0")
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
        with self.settings(USE_TZ=True):
            self.assertEqual(Version.objects.get_for_date(self.test, datetime.datetime.now(UTC())).field_dict["name"], "test1.2")
    
    def testCanRevert(self):
        """Tests that an object can be reverted to a previous revision."""
        oldest = Version.objects.get_for_object(self.test)[0]
        self.assertEqual(oldest.field_dict["name"], "test1.0")
        oldest.revert()
        self.assertEqual(self.model.objects.get().name, "test1.0")
        
    def testCanGetDeleted(self):
        """Tests that deleted objects can be retrieved."""
        self.assertEqual(len(Version.objects.get_deleted(self.model)), 0)
        # Create and delete another model.
        with reversion.revision:
            test2 = self.model.objects.create(name="test2.0")
        test2.delete()
        # Delete the test model.
        self.test.delete()
        # Ensure that there are now two deleted models.
        deleted = Version.objects.get_deleted(self.model)
        self.assertEqual(len(deleted), 2)
        self.assertEqual(deleted[0].field_dict["name"], "test1.2")
        self.assertEqual(deleted[1].field_dict["name"], "test2.0")
        self.assertEqual(len(deleted), 2)
        
    def testCanRecoverDeleted(self):
        """Tests that a deleted object can be recovered."""
        self.test.delete()
        # Ensure deleted.
        self.assertEqual(self.model.objects.count(), 0)
        # Recover.
        Version.objects.get_deleted(self.model)[0].revert()
        # Ensure recovered.
        self.assertEqual(self.model.objects.get().name, "test1.2")
    
    def testCanGenerateStatistics(self):
        """Tests that the stats are accurate for Version models."""
        self.assertEqual(Version.objects.filter(type=VERSION_ADD).count(), 1)
        self.assertEqual(Version.objects.filter(type=VERSION_CHANGE).count(), 2)
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 0)
        with reversion.revision:
            self.test.delete()
        self.assertEqual(Version.objects.filter(type=VERSION_DELETE).count(), 1)
        
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(self.model)
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        # Clear references.
        del self.test


class ReversionQueryStrPrimaryTest(ReversionQueryTest):

    model = ReversionTestModelStrPrimary
        
        
class ReversionCustomRegistrationTest(TestCase):
    
    """Tests the custom model registration options."""
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        # Register the model.
        reversion.register(ReversionTestModel, fields=("id",), format="xml")
        # Create some initial revisions.
        with reversion.revision:
            self.test = ReversionTestModel.objects.create(name="test1.0")
        with reversion.revision:
            self.test.name = "test1.1"
            self.test.save()
        with reversion.revision:
            self.test.name = "test1.2"
            self.test.save()
            
    def testCustomRegistrationHonored(self):
        """Ensures that the custom settings were honored."""
        self.assertEqual(tuple(reversion.revision.get_adapter(ReversionTestModel).get_fields_to_serialize()), ("id",))
        self.assertEqual(reversion.revision.get_adapter(ReversionTestModel).get_serialization_format(), "xml")
        
    def testCanRevertOnlySpecifiedFields(self):
        """"Ensures that only the restricted set of fields are loaded."""
        Version.objects.get_for_object(self.test)[0].revert()
        self.assertEqual(ReversionTestModel.objects.get().name, "")
            
    def testCustomSerializationFormat(self):
        """Ensures that the custom serialization format is used."""
        self.assertEquals(Version.objects.get_for_object(self.test)[0].serialized_data[0], "<");
    
    def testIgnoreDuplicates(self):
        """Ensures that duplicate revisions can be ignores."""
        self.assertEqual(len(Version.objects.get_for_object(self.test)), 3)
        with reversion.revision:
            self.test.save()
        self.assertEqual(len(Version.objects.get_for_object(self.test)), 4)
        with reversion.revision:
            reversion.revision.ignore_duplicates = True
            self.assertTrue(reversion.revision.ignore_duplicates)
            self.test.save()
        self.assertEqual(len(Version.objects.get_for_object(self.test)), 4)
            
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(ReversionTestModel)
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        # Clear references.
        del self.test
        
        
class TestRelatedModel(models.Model):
    
    """A model used to test Reversion relation following."""
    
    name = models.CharField(max_length=100)
    
    relation = models.ForeignKey(ReversionTestModel)
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class ReversionRelatedTest(TestCase):
    
    """Tests the ForeignKey and OneToMany support."""
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        TestRelatedModel.objects.all().delete()
        # Register the models.
        reversion.register(ReversionTestModel, follow=("testrelatedmodel_set",))
        reversion.register(TestRelatedModel, follow=("relation",))
    
    def testCanCreateRevisionForiegnKey(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test = ReversionTestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        self.assertEqual(Version.objects.get_for_object(test).count(), 1)
        self.assertEqual(Version.objects.get_for_object(related).count(), 1)
        self.assertEqual(Revision.objects.count(), 1)
        self.assertEqual(Version.objects.get_for_object(test)[0].revision.version_set.all().count(), 2)
        
    def testCanCreateRevisionOneToMany(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test = ReversionTestModel.objects.create(name="test1.0")
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
            test = ReversionTestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.name = "test1.1"
            test.save()
            related.name = "related1.1"
            related.save()
        # Attempt revert.
        Version.objects.get_for_object(test)[0].revision.revert()
        self.assertEqual(ReversionTestModel.objects.get().name, "test1.0")
        self.assertEqual(TestRelatedModel.objects.get().name, "related1.0")
    
    def testCanRevertDeleteRevistion(self):
        """Tests that an entire revision can be reverted with the delete functionality enabled."""
        with reversion.revision:
            test = ReversionTestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related-a-1.0", relation=test)
        with reversion.revision:
            related2 = TestRelatedModel.objects.create(name="related-b-1.0", relation=test)
            test.name = "test1.1"
            test.save()
            related.name = "related-a-1.1"
            related.save()
        # Attempt revert with delete.
        Version.objects.get_for_object(test)[0].revision.revert(delete=True)
        self.assertEqual(ReversionTestModel.objects.get().name, "test1.0")
        self.assertEqual(TestRelatedModel.objects.get(id=related.id).name, "related-a-1.0")
        self.assertEqual(TestRelatedModel.objects.filter(id=related2.id).count(), 0)
        self.assertEqual(TestRelatedModel.objects.count(), 1)
        
    def testCanRecoverRevision(self):
        """Tests that an entire revision can be recovered."""
        with reversion.revision:
            test = ReversionTestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.name = "test1.1"
            test.save()
            related.name = "related1.1"
            related.save()
        # Delete the models.
        test.delete()
        # Ensure deleted.
        self.assertEqual(ReversionTestModel.objects.count(), 0)
        self.assertEqual(TestRelatedModel.objects.count(), 0)
        # Query the deleted models..
        self.assertEqual(len(Version.objects.get_deleted(ReversionTestModel)), 1)
        self.assertEqual(len(Version.objects.get_deleted(TestRelatedModel)), 1)
        # Revert the revision.
        Version.objects.get_deleted(ReversionTestModel)[0].revision.revert()
        # Ensure reverted.
        self.assertEqual(ReversionTestModel.objects.count(), 1)
        self.assertEqual(TestRelatedModel.objects.count(), 1)
        # Ensure correct version.
        self.assertEqual(ReversionTestModel.objects.get().name, "test1.1")
        self.assertEqual(TestRelatedModel.objects.get().name, "related1.1")
    
    def testIgnoreDuplicates(self):
        """Ensures the ignoring duplicates works across a foreign key."""
        with reversion.revision:
            test = ReversionTestModel.objects.create(name="test1.0")
            related = TestRelatedModel.objects.create(name="related1.0", relation=test)
        with reversion.revision:
            test.name = "test1.1"
            test.save()
            related.name = "related1.1"
            related.save()
        self.assertEqual(len(Version.objects.get_for_object(test)), 2)
        with reversion.revision:
            test.save()
        self.assertEqual(len(Version.objects.get_for_object(test)), 3)
        with reversion.revision:
            test.save()
            reversion.revision.ignore_duplicates = True
        self.assertEqual(len(Version.objects.get_for_object(test)), 3)
    
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the models.
        reversion.unregister(ReversionTestModel)
        reversion.unregister(TestRelatedModel)
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        TestRelatedModel.objects.all().delete()


class TestManyToManyModel(models.Model):
    
    """A model used to test Reversion M2M relation following."""
    
    name = models.CharField(max_length=100)
    
    relations = models.ManyToManyField(ReversionTestModel)
    
    class Meta:
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class ReversionManyToManyTest(TestCase):
    
    """Tests the ManyToMany support."""
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        TestManyToManyModel.objects.all().delete()
        # Register the models.
        reversion.register(ReversionTestModel, follow=("testmanytomanymodel_set",))
        reversion.register(TestManyToManyModel, follow=("relations",))
    
    def testCanCreateRevision(self):
        """Tests that a revision containing both models is created."""
        with reversion.revision:
            test1 = ReversionTestModel.objects.create(name="test1.0")
            test2 = ReversionTestModel.objects.create(name="test2.0")
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
            test = ReversionTestModel.objects.create(name="test1.0")
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
            test1 = ReversionTestModel.objects.create(name="test1.0")
            test2 = ReversionTestModel.objects.create(name="test2.0")
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
        self.assertEqual(ReversionTestModel.objects.get(pk=test1.pk).name, "test1.0")
        self.assertEqual(ReversionTestModel.objects.get(pk=test2.pk).name, "test2.0")
        self.assertEqual(TestManyToManyModel.objects.get().name, "related1.0")
        
    def testCanRecoverRevision(self):
        """Tests that an entire revision can be recovered."""
        with reversion.revision:
            test1 = ReversionTestModel.objects.create(name="test1.0")
            test2 = ReversionTestModel.objects.create(name="test2.0")
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
        self.assertEqual(ReversionTestModel.objects.count(), 0)
        self.assertEqual(TestManyToManyModel.objects.count(), 0)
        # Query the deleted models..
        self.assertEqual(len(Version.objects.get_deleted(ReversionTestModel)), 2)
        self.assertEqual(len(Version.objects.get_deleted(TestManyToManyModel)), 1)
        # Revert the revision.
        Version.objects.get_deleted(TestManyToManyModel)[0].revision.revert()
        # Ensure reverted.
        self.assertEqual(ReversionTestModel.objects.count(), 2)
        self.assertEqual(TestManyToManyModel.objects.count(), 1)
        # Ensure correct version.
        self.assertEqual(ReversionTestModel.objects.get(pk=test1_pk).name, "test1.1")
        self.assertEqual(ReversionTestModel.objects.get(pk=test2_pk).name, "test2.1")
        self.assertEqual(TestManyToManyModel.objects.get().name, "related1.1")
    
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the models.
        reversion.unregister(ReversionTestModel)
        reversion.unregister(TestManyToManyModel)
        # Clear the database.
        Revision.objects.all().delete()
        ReversionTestModel.objects.all().delete()
        TestManyToManyModel.objects.all().delete()


class ReversionCreateInitialRevisionsTest(TestCase):

    """Tests that the createinitialrevisions command works."""
    
    model = ReversionTestModel
    
    def setUp(self):
        """Sets up the ReversionTestModel."""
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        # Register the model.
        reversion.register(self.model)
        # Create some initial revisions.
        self.test = self.model.objects.create(name="test1.0")
    
    def testCreateInitialRevisions(self):
        self.assertEqual(Version.objects.get_for_object(self.test).count(), 0)
        call_command("createinitialrevisions", verbosity=0)
        self.assertEqual(Version.objects.get_for_object(self.test).count(), 1)
        
    def tearDown(self):
        """Tears down the tests."""
        # Unregister the model.
        reversion.unregister(self.model)
        # Clear the database.
        Revision.objects.all().delete()
        self.model.objects.all().delete()
        # Clear references.
        del self.test
        
        
class ReversionCreateInitialRevisionsStrPrimaryTest(ReversionCreateInitialRevisionsTest):

    model = ReversionTestModelStrPrimary
