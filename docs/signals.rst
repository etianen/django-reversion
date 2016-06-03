.. _signals:

Signals
=======

django-reversion provides a number of custom signals.


reversion.signals.pre_revision_commit
-------------------------------------

Sent just before a revision is saved to the database.

``sender``
    The :ref:`RevisionManager` creating the revision.

``instances``
    An iterable of model instances in the revision.

``revision``
    The unsaved :ref:`Revision` model.

``versions``
    The unsaved :ref:`Version` models in the revision.


reversion.signals.post_revision_commit
--------------------------------------

Sent just after a revision is saved to the database.

``sender``
    The :ref:`RevisionManager` creating the revision.

``instances``
    An iterable of model instances in the revision.

``revision``
    The saved :ref:`Revision` model.

``versions``
    The saved :ref:`Version` models in the revision.
