"""Revision management for Reversion."""


import threading

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.db import transaction
from django.core import serializers


class RevisionManagementError(Exception):
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    pass


thread_locals = threading.local()


def get_versions():
    """Returns the list of versions in the current revision."""
    try:
        return thread_locals.versions
    except AttributeError:
        thread_locals.versions = {}
        return get_versions()


def get_depth():
    """Returns the current depth of the revision management stack."""
    try:
        return thread_locals.depth
    except AttributeError:
        thread_locals.depth = 0
        return get_depth()


def is_managed():
    """Returns whether the current thread is under revision management."""
    return get_depth() > 0


def is_dirty():
    """Returns whether the current revision has pending revisions."""
    return bool(get_versions())


def start():
    """Starts a block of revision management."""
    thread_locals.depth = get_depth() + 1


def end():
    """Ends a block of revision management."""
    if thread_locals.depth <= 0:
        raise RevisionManagementError, "There is no active revision for this thread."


def add(model, commit=False):
    """
    Registers a model with the given revision.
    
    If commit is True, then the model will be serialized immediately.  It is
    best to leave this as False, so as to catch any M2M relationships.  The only
    time you would need to commit immediately is if the models is about to be
    deleted.
    """
    if is_managed():
        if commit:
            serialized_data = serializers.serialize("xml", [model])
        else:
            serialized_data = None
        get_versions()[model] = (model.pk, serialized_data) 
        # Save parent models.
        for field in model._meta.parents.values():
            if hasattr(model, field.get_cache_name()):
                delattr(model, field.get_cache_name())  # Clear parent cache.
            add(getattr(model, field.name), commit)
    else:
        create_revision(lambda: add(model, commit))()


def commit():
    """Commits all versions in the current revision."""
    from django.contrib.contenttypes.models import ContentType
    from reversion.models import Version
    revision_start = None
    for version, version_data in get_versions().items():
        print version_data
        object_id, serialized_data = version_data
        if not serialized_data:
            serialized_data = serializers.serialize("xml", [version])
        saved_version = Version.objects.create(content_type=ContentType.objects.get_for_model(version),
                                               object_id=unicode(object_id),
                                               serialized_data=serialized_data,
                                               revision_start=revision_start)
        revision_start = revision_start or saved_version
    get_versions().clear()
    
    
def rollback():
    """Removes all versions from the current revision."""
    get_versions().clear()
    
    
# Decorators.

def create_revision(func):
    """Decorator that groups all saved versions into a revision."""
    def _create_revision(*args, **kwargs):
        try:
            start()
            try:
                result = func(*args, **kwargs)
            except:
                rollback()
                raise
            else:
                commit()
            return result
        finally:
            end()
    _create_revision = transaction.commit_on_success(_create_revision)
    return wraps(func)(_create_revision)