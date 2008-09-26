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
    get_revision_stack().append(([], []))
    
    
def commit_revision(revision, revision_start=None):
    """Saves this revision and all child revisions."""
    models, nested = revision
    if models:
        parent = Version.objects.create(object_version=models[0], revision_start=revision_start)
    for model in models[1:]:
        Version.objects.create(object_version=models[0], revision_start=revision_start)
    for sub_revision in nested:
        commit_revision(sub_revision, parent)
    
    
def end():
    """Leaves transaction managment for a running thread."""
    # Clear revision state.
    current_revisions = get_revision_stack()
    try:
        revision = current_revisions.pop()
    except IndexError:
        raise RevisionManagementError, "There is no active revision for this thread."
    if current_revisions:
        # This was a nested revision.
        current_revisions[-1][1].append(revision)
    else:
        # This was the top-level revision... time to commit.
        commit_revision(revision)
        
    
    
def is_managed():
    """Returns whether the current thread is under revision management."""
    return bool(get_revision_stack())


def add(model):
    """Registers a model with the given revision."""
    if is_managed():
        revision_stack = get_revision_stack()[-1][0].append(model)
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