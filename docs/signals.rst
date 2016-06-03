.. _signals:

Signals
=======

django-reversion provides a number of custom signals.


Signal reference
----------------

reversion.signals.pre_revision_commit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sent just before a revision is saved to the database.

``sender``
    The ``RevisionManager`` creating the revision.

``instances``
    An iterable of model instances in the revision.

``revision``
    The unsaved ``Revision`` model.

``versions``
    The unsaved ``Version`` models in the revision.


reversion.signals.post_revision_commit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sent just after a revision is saved to the database.

``sender``
    The ``RevisionManager`` creating the revision.

``instances``
    An iterable of model instances in the revision.

``revision``
    The saved ``Revision`` model.

``versions``
    The saved ``Version`` models in the revision.
