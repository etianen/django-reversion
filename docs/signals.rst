.. _signals:

Signals
=======

django-reversion provides two custom signals.


reversion.signals.pre_revision_commit
-------------------------------------

Sent just before a revision is saved to the database.

.. include:: /_include/signal-args.rst


reversion.signals.post_revision_commit
--------------------------------------

Sent just after a revision and its related versions are saved to the database.

.. include:: /_include/signal-args.rst
