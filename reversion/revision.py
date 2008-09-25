"""Revision management for Reversion."""


import threading, weakref

from reversion.models import Revision, Version

from django.db import transaction


revisions = weakref.WeakKeyDictionary()


class RevisionManagementError(Exception):
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    pass


def start(comment=None, user=None):
    """Enters transaction management for a running thread."""
    current_thread = threading.currentThread()
    revisions.setdefault(current_thread, [])
    revisions[current_thread].append((comment, user))
    
    
def end():
    """Leaves transaction managment for a running thread."""
    # Clear revision state.
    revisions[threading.currentThread()].pop()
    
    
def is_managed():
    """Returns whether the current thread is under revision management."""
    return bool(revisions.get(threading.currentThread()))


def get_current_revision():
    """Returns the currently open revision."""
    current_revisions = revisions[threading.currentThread()]
    revision = current_revisions[-1]
    if not isinstance(revision, Revision):
        if len(current_revisions) > 1:
            parent = current_revisions[-2]
        else:
            parent = None
        comment, user = revision
        revision = Revision.objects.create(comment=comment, user=user)
        current_revisions[-1] = revision
    return revision


def add(model):
    """Registers a model with the given revision."""
    if is_managed():
        # Create Revision model if required.
        revision = get_current_revision()
        # Create version and add to revision.
        version = Version.objects.create(revision=revision,
                                         object_version=model)
        return version
    else:
        start()
        try:
            return add(model)
        finally:
            end()
    
    
# Decorators.

def create_revision(func):
    """
    Decorator that groups all saved versions into a revision.
    
    The function will also be wrapped in a database transaction.
    """
    def wrapper(*args, **kwargs):
        start()
        try:
            return func(*args, **kwargs)
        finally:
            end()
    return transaction.commit_on_success(wrapper)