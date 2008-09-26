"""Revision management for Reversion."""


import threading

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from reversion.models import Version


thread_locals = threading.local()


class RevisionManagementError(Exception):
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    pass


def start():
    """Enters revision management for a running thread."""
    if not hasattr(thread_locals, "versions"):
        thread_locals.versions = set()
    if not hasattr(thread_locals, "depth"):
        thread_locals.depth = 0
    thread_locals.depth += 1
        
    
def end():
    """Leaves revision managment for a running thread."""
    try:
        thread_locals.depth -= 1
    except AttributeError:
        raise RevisionManagementError, "There is no active revision for this thread."
    if thread_locals.depth == 0:
        # This is the top-level in the revision stack... time to commit.
        try:
            revision_start = None
            for version in thread_locals.versions:
                saved_version = Version.objects.create(object_version=version, revision_start=revision_start)
                revision_start = revision_start or saved_version
        finally:
            del thread_locals.depth
            del thread_locals.versions
        
        
def is_managed():
    """Returns whether the current thread is under revision management."""
    return hasattr(thread_locals, "versions")


def add(model):
    """Registers a model with the given revision."""
    if is_managed():
        thread_locals.versions.add(model)
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
            return func(*args, **kwargs)
        finally:
            end()
    return wraps(func)(_create_revision)