.. _signals:

Signals
=======

django-reversion provides a number of custom signals.


reversion.pre_revision_commit
-----------------------------

Sent just before a revision is saved to the database.

.. include:: /_include/signal-args.rst


reversion.post_revision_commit
------------------------------

Sent just after a revision is saved to the database.

.. include:: /_include/signal-args.rst
