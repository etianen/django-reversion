"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

from django.db import models
from django.test import TestCase

import reversion
from reversion.revisions import RegistrationError


class TestModelBase(models.Model):

    name = models.CharField(
        max_length = 100,
    )
    
    def __unicode__(self):
        return self.title

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


# Import the depricated tests.
from reversion import tests_depricated

for name, value in vars(tests_depricated).iteritems():
    if isinstance(value, type) and issubclass(value, TestCase):
        globals()[name] = value
del name
del value