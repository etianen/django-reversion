"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

from django.test import TestCase


# Import the depricated tests.
from reversion import tests_depricated

for name, value in vars(tests_depricated).iteritems():
    if isinstance(value, type) and issubclass(value, TestCase):
        globals()[name] = value
del name
del value