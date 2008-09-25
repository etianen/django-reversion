"""Revision management for Reversion."""


import threading, weakref

from reversion.models import Revision, Version


revisions = weakref.WeakKeyDictionary()


class RevisionManagementError(Exception):
    
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    
    pass


def start(comment=""):
    """Enters transaction management for a running thread."""
    current_thread = threading.currentThread()
    revisions.setdefault(current_thread, [])
    revisions[current_thread].append(comment)
    
    
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
        # Create revisions as required.
        parent = None
        for n in range(len(current_revisions)):
            if isinstance(current_revisions[n], basestring):
                current_revisions[n] = Revision.objects.create(parent=parent,
                                                               comment=current_revisions[n])
            parent = current_revisions[n]
        # Create version and add to revision.
        version = Version.objects.create(revision=current_revisions[-1],
                                         object_version=model)
        return version
    else:
        start()
        try:
            return add(model)
        finally:
            end()
    