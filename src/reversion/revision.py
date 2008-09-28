"""Revision management for Reversion."""


import threading

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.core import serializers
from django.db import transaction


thread_locals = threading.local()


class RevisionManagementError(Exception):
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    pass


def start():
    """Enters revision management for a running thread."""
    if not hasattr(thread_locals, "versions"):
        thread_locals.versions = {}
    if not hasattr(thread_locals, "depth"):
        thread_locals.depth = 0
    if not hasattr(thread_locals, "committed"):
        thread_locals.committed = {}
    thread_locals.depth += 1
    # Start a database transaction.
    transaction.enter_transaction_management()
    transaction.managed(True)
        
    
def end():
    """Leaves revision managment for a running thread."""
    try:
        thread_locals.depth -= 1
    except AttributeError:
        raise RevisionManagementError, "There is no active revision for this thread."
    if thread_locals.depth == 0:
        from django.contrib.contenttypes.models import ContentType
        from reversion.models import Version
        # This is the top-level in the revision stack... time to commit.
        try:
            try:
                revision_start = None
                for version, object_id in thread_locals.versions.items():
                    if not (version.__class__, object_id) in thread_locals.committed:
                        thread_locals.committed[(version.__class__, object_id)] = serializers.serialize("xml", [version])
                    serialized_data = thread_locals.committed[(version.__class__, object_id)]
                    saved_version = Version.objects.create(content_type=ContentType.objects.get_for_model(version),
                                                           object_id=object_id,
                                                           serialized_data=serialized_data,
                                                           revision_start=revision_start)
                    revision_start = revision_start or saved_version
                if transaction.is_dirty():
                    transaction.commit()
            except:
                if transaction.is_dirty():
                    transaction.rollback()
                raise
        finally:
            del thread_locals.depth
            del thread_locals.versions
            del thread_locals.committed
            transaction.leave_transaction_management()
        
        
def is_managed():
    """Returns whether the current thread is under revision management."""
    return hasattr(thread_locals, "versions")


def add(model, commit=False):
    """
    Registers a model with the given revision.
    
    If commit is True, then the model will be serialized immediately.  It is
    best to leave this as False, so as to catch any M2M relationships.
    """
    if is_managed():
        thread_locals.versions[model] = model.pk
        if commit:
            thread_locals.committed[(model.__class__, model.pk)] = serializers.serialize("xml", [model]) 
        # Save parent models.
        for field in model._meta.parents.values():
            if hasattr(model, field.get_cache_name()):
                delattr(model, field.get_cache_name())  # Clear parent cache.
            add(getattr(model, field.name), commit)
    else:
        start()
        try:
            return add(model)
        finally:
            end()
    
    
# Decorators.

def create_revision(func):
    """Decorator that groups all saved versions into a revision."""
    def _create_revision(*args, **kwargs):
        start()
        try:
            try:
                return func(*args, **kwargs)
            except:
                if transaction.is_dirty():
                    transaction.rollback()
                raise
        finally:
            end()
    return wraps(func)(_create_revision)