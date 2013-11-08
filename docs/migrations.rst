.. _migrations:

Schema migrations
=================


This page describes the schema migrations that have taken place over the lifetime of django-reversion, along with a how-to guide for updating your schema using `South <http://south.aeracode.org/>`_.


django-reversion 1.8
--------------------

The current working version removes ``type`` column from ``reversion_version`` table.

In order to apply this migration using south, simply run::

    ./manage.py migrate reversion
    

django-reversion 1.5
--------------------

This version adds in significant speedups for models with integer primary keys.

In order to apply this migration using south, simply run::

    ./manage.py migrate reversion
    
If you have a large amount of existing version data, then this command might take a little while to run while the database tables are updated.


django-reversion 1.4
--------------------

This version added a much-requested 'type' field to Version models, allows statistic to be gathered about the number of additions, changes and deletions that have been applied to a model.

In order to apply this migration, it is first necessary to install South.

1. Add 'south' to your ``INSTALLED_APPS`` setting.
2. Run ``./manage.py syncdb``

You then need to run the following two commands to complete the migration::

    ./manage.py migrate reversion 0001 --fake
    ./manage.py migrate reversion


django-reversion 1.3.3
----------------------

No migration needed.
