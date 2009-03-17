"""Revision management for Reversion."""


try:
    set
except NameError:
    from sets import Set as set  # Python 2.3 fallback.

import sys

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local  # Python 2.3 fallback.

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import models
from django.db.models.query import QuerySet

from reversion.helpers import add_to_revision
from reversion.models import Revision, Version
from reversion.registration import get_registration_info


class RevisionManagementError(Exception):
    
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    
    pass


class RevisionManager(local):
    
    """Manages the state of the current revision."""
    
    def __init__(self):
        """Initializes the RevisionManager."""
        self._clear()
    
    def _clear(self):
        """Puts the revision manager back into its default state."""
        self._versions = set()
        self._user = None
        self._comment = None
        self._depth = 0
        self._is_invalid = False
        self._meta = []
        
    def start(self):
        """Begins a revision."""
        self._depth += 1
        
    def is_active(self):
        """Returns whether there is an active revision for this thread."""
        return self._depth > 0
    
    def _assert_active(self):
        """Checks for an active revision, throwning an exception if none."""
        if not self.is_active():
            raise RevisionManagementError, "There is no active revision for this thread."
        
    def _add(self, obj):
        """
        Adds an object to the current revision.
        
        If `fields` is specified, then only the named fields will be serialized.
        
        If `follow` is specified, then the named foreign relationships will also
        be included in the revision.  `follow` can be specified as a list of
        relationship names, or as a dictionary mapping relationship names to
        a list of fields to be serialized.
        """
        self._assert_active()
        self._versions.add(obj)
        
    def set_user(self, user):
        """Sets the user for the current revision"""
        self._assert_active()
        self._user = user
        
    def get_user(self):
        """Gets the user for the current revision."""
        self._assert_active()
        return self._user
    
    user = property(get_user,
                    set_user,
                    doc="The user for the current revision.")
        
    def set_comment(self, comment):
        """Sets the comment for the current revision"""
        self._assert_active()
        self._comment = comment
        
    def get_comment(self):
        """Gets the comment for the current revision."""
        self._assert_active()
        return self._comment
    
    comment = property(get_comment,
                       set_comment,
                       doc="The comment for the current revision.")
        
    def add_meta(self, cls, **kwargs):
        """Adds a class of mete information to the current revision."""
        self._assert_active()
        self._meta.append((cls, kwargs))
        
    def invalidate(self):
        """Marks this revision as broken, so should not be commited."""
        self._assert_active()
        self._is_invalid = True
        
    def end(self):
        """Ends a revision."""
        self._assert_active()
        self._depth -= 1
        # Handle end of revision conditions here.
        if self._depth == 0:
            try:
                if self._versions and not self._is_invalid:
                    # Save a new revision.
                    revision = Revision.objects.create(user=self._user,
                                                       comment=self._comment)
                    revision_set = set()
                    # Follow relationships.
                    for version in self._versions:
                        add_to_revision(version, revision_set)
                    # Save version models.
                    for obj in revision_set:
                        fields, follow, format = get_registration_info(obj.__class__)
                        object_id = unicode(obj.pk)
                        content_type = ContentType.objects.get_for_model(obj)
                        serialized_data = serializers.serialize(format, [obj], fields=fields)
                        Version.objects.create(revision=revision,
                                               object_id=object_id,
                                               content_type=content_type,
                                               format=format,
                                               serialized_data=serialized_data,
                                               object_repr=unicode(obj))
                    for meta_cls, meta_kwargs in self._meta:
                        meta_cls._default_manager.create(revision=revision, **meta_kwargs)
            finally:
                self._clear()
        return False
        
    def post_save_receiver(self, instance, sender, **kwargs):
        """Saves a new version of registered models."""
        if self.is_active():
            self._add(instance)
        
    def __enter__(self):
        """Enters a block of revision management."""
        self.start()
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Leaves a block of revision management."""
        if exc_type is not None:
            self.invalidate()
        self.end()
        return False
        
    def create_on_success(self, func):
        """Creates a revision when the given function exist successfully."""
        def _create_on_success(*args, **kwargs):
            self.start()
            try:
                try:
                    result = func(*args, **kwargs)
                except:
                    self.invalidate()
                    raise
            finally:
                self.end()
            return result
        return wraps(func)(_create_on_success)

        
# A thread-safe shared revision manager.
revision = RevisionManager()