.. _commands:

Management commands
===================

django-reversion includes a number of ``django-admin.py`` management commands.


.. _createinitialrevisions:

createinitialrevisions
----------------------

Creates an initial revision for all registered models in your project. It should be run after installing django-reversion, or registering a new model with django-reversion.

.. code:: bash

    ./manage.py createinitialrevisions
    ./manage.py createinitialrevisions your_app.YourModel --comment="Initial revision."
    ./manage.py createinitialrevisions your_app.YourModel --user=historian --date-created="2020-09-28T12:34:56+00:00"
    ./manage.py createinitialrevisions your_app.YourModel --meta="{\"your_app.RevisionMeta\": {\"hello\": \"world\"}}"

Run ``./manage.py createinitialrevisions --help`` for more information.

``--user`` looks up an existing user by the configured user model's username
field, in the database selected for revision data (``--using``). Omitting it
leaves the default revision user unchanged.

``--date-created`` sets the same creation time on every new revision. Timestamps
without a UTC offset are interpreted in ``settings.TIME_ZONE``. If
``USE_TZ=False``, timestamps with an offset are converted to that time zone and
stored without time zone information. Invalid timestamps and unknown users are
rejected before creating any revisions. Omitting the option preserves the
current-time default.

.. Warning::
    For large databases, this command can take a long time to run.


deleterevisions
---------------

Deletes old revisions. It can be run regularly to keep revision history manageable.

.. code:: bash

    ./manage.py deleterevisions
    # keep any changes from last 30 days
    ./manage.py deleterevisions your_app.YourModel --days=30
    # keep 30 most recent changes for each item.
    ./manage.py deleterevisions your_app.YourModel --keep=30
    # Keep anything from last 30 days and at least 3 from older changes.
    ./manage.py deleterevisions your_app.YourModel --keep=3 --days=30

Run ``./manage.py deleterevisions --help`` for more information.

.. Warning::
    With no arguments, this command will delete your entire revision history! Read the command help for ways to limit which revisions should be deleted.
