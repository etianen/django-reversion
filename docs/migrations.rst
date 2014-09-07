.. _migrations:

Schema migrations
=================


This page describes the schema migrations that have taken place over the lifetime of django-reversion, along with a how-to guide for updating your schema.


django-reversion 1.8.3
----------------------

This release adds an index to the ``date_created`` column on the ``reversion_revision`` table.

In order to apply this migration using south, simply run::

    ./manage.py migrate reversion

**Important:** South 1.0 or greater is required to run these migrations.

This release also starts using the django core `migrations framework <https://docs.djangoproject.com/en/dev/topics/migrations/>`_, which is intended to be used as the community standard going forwards. To `upgrade from south <https://docs.djangoproject.com/en/dev/topics/migrations/#upgrading-from-south>`_, please complete the following steps:

1. Ensure that your app is up-to-date with all django-reversion migrations.
2. Upgrade to Django 1.7 or greater.
3. Remove ``'south'`` from ``INSTALLED_APPS``.
4. Run ``./manage.py migrate reversion``.

The legacy south migrations will be removed from django-reversion in release 1.9.


django-reversion 1.8
--------------------

This release removes ``type`` column from ``reversion_version`` table.

In order to apply this migration using south, simply run::

    ./manage.py migrate reversion
    

django-reversion 1.5
--------------------

This release adds in significant speedups for models with integer primary keys.

In order to apply this migration using south, simply run::

    ./manage.py migrate reversion
    
If you have a large amount of existing version data, then this command might take a little while to run while the database tables are updated.


django-reversion 1.4
--------------------

This release added a much-requested 'type' field to Version models, allows statistic to be gathered about the number of additions, changes and deletions that have been applied to a model.

In order to apply this migration, it is first necessary to install South.

1. Add 'south' to your ``INSTALLED_APPS`` setting.
2. Run ``./manage.py syncdb``

You then need to run the following two commands to complete the migration::

    ./manage.py migrate reversion 0001 --fake
    ./manage.py migrate reversion


django-reversion 1.3.3
----------------------

No migration needed.
