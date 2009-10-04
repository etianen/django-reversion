"""Revision management for Reversion."""


try:
    set
except NameError:
    from sets import Set as set  # Python 2.3 fallback.

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local  # Python 2.3 fallback.

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

import sys

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import post_save

from reversion.models import Revision, Version
from reversion.storage import VersionFileStorageWrapper


class RevisionManagementError(Exception):
    
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    

class RegistrationError(Exception):
    
    """Exception thrown when registration with Reversion goes wrong."""


class RegistrationInfo(object):
    
    """Stored registration information about a model."""
    
    __slots__ = "fields", "file_fields", "follow", "format",
    
    def __init__(self, fields, file_fields, follow, format):
        """Initializes the registration info."""
        self.fields = fields
        self.file_fields = file_fields
        self.follow = follow
        self.format = format
          
          
class RevisionState(local):
    
    """Manages the state of the current revision."""
    
    def __init__(self):
        """Initializes the revision state."""
        self.clear()
    
    def clear(self):
        """Puts the revision manager back into its default state."""
        self.objects = set()
        self.user = None
        self.comment = ""
        self.depth = 0
        self.is_invalid = False
        self.meta = []
   

DEFAULT_SERIALIZATION_FORMAT = "xml"
   
   
class RevisionManager(object):
    
    """Manages the configuration and creation of revisions."""
    
    __slots__ = "__weakref__", "_registry", "_state",
    
    def __init__(self):
        """Initializes the revision manager."""
        self._registry = {}
        self._state = RevisionState()

    # Registration methods.

    def is_registered(self, model_class):
        """
        Checks whether the given model has been registered with this revision
        manager.
        """
        return model_class in self._registry
        
    def register(self, model_class, fields=None, follow=(), format=DEFAULT_SERIALIZATION_FORMAT):
        """Registers a model with this revision manager."""
        # Prevent multiple registration.
        if self.is_registered(model_class):
            raise RegistrationError, "%r has already been registered with Reversion." % model_class
        # Ensure the parent model of proxy models is registered.
        if model_class._meta.proxy and not self.is_registered(model_class._meta.parents.keys()[0]):
            raise RegistrationError, "%r is a proxy model, and its parent has not been registered with Reversion." % model_class
        # Calculate serializable model fields.
        opts = model_class._meta
        local_fields = opts.local_fields + opts.local_many_to_many
        if fields is None:
            fields = [field.name for field in local_fields]
        fields = tuple(fields)
        # Calculate serializable model file fields.
        file_fields = []
        for field in local_fields:
            if isinstance(field, models.FileField) and field.name in fields:
                field.storage = VersionFileStorageWrapper(field.storage)
                file_fields.append(field)
        file_fields = tuple(file_fields)
        # Register the generated registration information.
        follow = tuple(follow)
        registration_info = RegistrationInfo(fields, file_fields, follow, format)
        self._registry[model_class] = registration_info
        # Connect to the post save signal of the model.
        post_save.connect(self.post_save_receiver, model_class)
    
    def get_registration_info(self, model_class):
        """Returns the registration information for the given model class."""
        try:
            registration_info = self._registry[model_class]
        except KeyError:
            raise RegistrationError, "%r has not been registered with Reversion." % model_class
        else:
            return registration_info
        
    def unregister(self, model_class):
        """Removes a model from version control."""
        try:
            registration_info = self._registry.pop(model_class)
        except KeyError:
            raise RegistrationError, "%r has not been registered with Reversion." % model_class
        else:
            for field in registration_info.file_fields:
                field.storage = field.storage.wrapped_storage
            post_save.disconnect(self.post_save_receiver, model_class)
    
    # Low-level revision management methods.
    
    def start(self):
        """
        Begins a revision for this thread.
        
        This MUST be balanced by a call to `end`.  It is recommended that you
        leave these methods alone and instead use the revision context manager
        or the `create_on_success` decorator.
        """
        self._state.depth += 1
        
    def is_active(self):
        """Returns whether there is an active revision for this thread."""
        return self._state.depth > 0
    
    def assert_active(self):
        """Checks for an active revision, throwning an exception if none."""
        if not self.is_active():
            raise RevisionManagementError, "There is no active revision for this thread."
    
    def add(self, obj):
        """Adds an object to the current revision."""
        self.assert_active()
        self._state.objects.add(obj)
        
    def set_user(self, user):
        """Sets the user for the current revision"""
        self.assert_active()
        self._state.user = user
        
    def get_user(self):
        """Gets the user for the current revision."""
        self.assert_active()
        return self._state.user
    
    user = property(get_user,
                    set_user,
                    doc="The user for the current revision.")
        
    def set_comment(self, comment):
        """Sets the comment for the current revision"""
        self.assert_active()
        self._state.comment = comment
        
    def get_comment(self):
        """Gets the comment for the current revision."""
        self.assert_active()
        return self._state.comment
    
    comment = property(get_comment,
                       set_comment,
                       doc="The comment for the current revision.")
        
    def add_meta(self, cls, **kwargs):
        """Adds a class of meta information to the current revision."""
        self.assert_active()
        self._state.meta.append((cls, kwargs))
        
    def invalidate(self):
        """Marks this revision as broken, so should not be commited."""
        self.assert_active()
        self._state.is_invalid = True
        
    def is_invalid(self):
        """Checks whether this revision is invalid."""
        return self._state.is_invalid
        
    def follow_relationships(self, object_set):
        """
        Follows all the registered relationships in the given set of models to
        yield a set containing the original models plus all their related
        models.
        """
        result_set = set()
        def _follow_relationships(obj):
            # Prevent recursion.
            if obj in result_set:
                return
            result_set.add(obj)
            # Follow relations.
            registration_info = self.get_registration_info(obj.__class__)
            for relationship in registration_info.follow:
                # Clear foreign key cache.
                try:
                    related_field = obj._meta.get_field(relationship)
                except models.FieldDoesNotExist:
                    pass
                else:
                    if isinstance(related_field, models.ForeignKey):
                        if hasattr(obj, related_field.get_cache_name()):
                            delattr(obj, related_field.get_cache_name())
                # Get the references obj(s).
                related = getattr(obj, relationship, None)
                if isinstance(related, models.Model):
                    _follow_relationships(related) 
                elif isinstance(related, (models.Manager, QuerySet)):
                    for related_obj in related.all():
                        _follow_relationships(related_obj)
                elif related is not None:
                    raise TypeError, "Cannot follow the relationship %r. Expected a model or QuerySet, found %r." % (relationship, related)
            # If a proxy model's parent is registered, add it.
            if obj._meta.proxy:
                parent_cls = obj._meta.parents.keys()[0]
                if self.is_registered(parent_cls):
                    parent_obj = parent_cls.objects.get(pk=obj.pk)
                    _follow_relationships(parent_obj)
        map(_follow_relationships, object_set)
        return result_set
        
    def end(self):
        """Ends a revision."""
        self.assert_active()
        self._state.depth -= 1
        # Handle end of revision conditions here.
        if self._state.depth == 0:
            models = self._state.objects
            try:
                if models and not self.is_invalid():
                    # Save a new revision.
                    revision = Revision.objects.create(user=self._state.user,
                                                       comment=self._state.comment)
                    # Follow relationships.
                    revision_set = self.follow_relationships(self._state.objects)
                    # Save version models.
                    for obj in revision_set:
                        # Proxy models should not actually be saved to the revision set.
                        if obj._meta.proxy:
                            continue
                        registration_info = self.get_registration_info(obj.__class__)
                        object_id = unicode(obj.pk)
                        content_type = ContentType.objects.get_for_model(obj)
                        serialized_data = serializers.serialize(registration_info.format, [obj], fields=registration_info.fields)
                        Version.objects.create(revision=revision,
                                               object_id=object_id,
                                               content_type=content_type,
                                               format=registration_info.format,
                                               serialized_data=serialized_data,
                                               object_repr=unicode(obj))
                    for cls, kwargs in self._state.meta:
                        cls._default_manager.create(revision=revision, **kwargs)
            finally:
                self._state.clear()
        
    # Signal receivers.
        
    def post_save_receiver(self, instance, sender, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self.is_active():
            self.add(instance)
       
    # High-level revision management methods.
        
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

