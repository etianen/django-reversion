"""Revision management for Reversion."""


import threading, weakref

from reversion.models import Revision, Version


revisions = weakref.WeakKeyDictionary()


class RevisionManagementError(Exception):
    
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    
    pass


def start(comment=None, user=None):
    """Enters transaction management for a running thread."""
    print "START", comment
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


def add(model):
    """Registers a model with the given revision."""
    if is_managed():
        current_revisions = revisions[threading.currentThread()]
        # Create Revision model if required.
        revision = current_revisions[-1]
        if not isinstance(revision, Revision):
            if len(current_revisions) > 1:
                parent = current_revisions[-2]
            else:
                parent = None
            comment, user = revision
            revision = Revision.objects.create(comment=comment, user=user)
            current_revisions[-1] = revision
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
    