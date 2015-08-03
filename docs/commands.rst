.. _commands:

Management commands
===================

django-reversion comes with a number of additional django-admin.py management commands, detailed below.

createinitialrevisions
----------------------

This command is used to create a single, base revision for all registered models in your project. It should be run after installing django-reversion, or registering a new model with django-reversion. If your project contains a lot of version-controlled data, then this might take a while to complete.

::

    django-admin.py createinitialrevisions
    django-admin.py createinitialrevisions someapp
    django-admin.py createinitialrevisions someapp.SomeModel

deleterevisions
----------------------

This command is used to delete old revisions. It can be run regularly to keep storage requirements of models history sane. You can specify to delete revisions older than N days or delete only revisions older than the specified date or keep only the N most recent revisions for each object.

::

    django-admin.py deleterevisions myapp
    django-admin.py deleterevisions --date=2015-01-15
    django-admin.py deleterevisions myapp.mymodel --days=365 --force
    django-admin.py deleterevisions myapp.mymodel --keep=10
