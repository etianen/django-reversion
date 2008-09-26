"""Revision management for Reversion."""


import threading, weakref

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from reversion.models import Version


revisions = weakref.WeakKeyDictionary()


class RevisionManagementError(Exception):
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    pass


def get_revision_stack():
    """Returns the stack of revisions for the current thread."""
    return revisions.setdefault(threading.currentThread(), [])


def start():
    """Enters transaction management for a running thread."""
    get_revision_stack().append(None)
    
    
def end():
    """Leaves transaction managment for a running thread."""
    # Clear revision state.
    try:
        revisions[threading.currentThread()].pop()
    except IndexError:
        raise RevisionManagementError, "There is no active revision for this thread."
    
    
def is_managed():
    """Returns whether the current thread is under revision management."""
    return bool(get_revision_stack())


def add(model):
    """Registers a model with the given revision."""
    if is_managed():
        revision_stack = get_revision_stack()
        revision_start = revision_stack[-1]
        if not revision_start and len(revision_stack) > 1:
            revision_start = revision_stack[-2]
        version = Version.objects.create(revision_start=revision_start,
                                         object_version=model)
        if not revision_stack[-1]:
            revision_stack[-1] = version
        return version
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