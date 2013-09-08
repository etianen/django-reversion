.. _commands:

Management commands
===================

django-reversion comes with a number of additional django-admin.py management commands, detailed below.

createinitialrevisions
----------------------

This command is used to create a single, base revision for all registered models in your project. It should be run after installing django-reversion. If your project contains a lot of version-controlled data, then this might take a while to complete.

::

    django-admin.py createinitialrevisions
    django-admin.py createinitialrevisions someapp
    django-admin.py createinitialrevisions someapp.SomeModel
