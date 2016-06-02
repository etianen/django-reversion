.. _index:

django-reversion
================

**django-reversion** is an extension to the Django web framework that provides
version control for model instances.


Features
--------

-  Roll back to any point in a model instance's history.
-  Recover deleted model instances.
-  Simple admin integration.


Getting started
---------------

To install django-reversion, follow these steps:

1.  Install with pip: ``pip install django-reversion``.
2.  Add ``'reversion'`` to ``INSTALLED_APPS``.
3.  Run ``manage.py migrate``.

If you are using anything older than the latest LTS release of Django, please check the :ref:`compatible Django versions <django-versions>` page before installing django-reversion.


Admin integration
-----------------

django-reversion can be used to add rollback and recovery facility to your admin site. Simply register your models with a subclass of ``reversion.VersionAdmin``::

    from reversion.admin import VersionAdmin

    class YourModelAdmin(VersionAdmin):

        pass

    admin.site.register(YourModel, YourModelAdmin)

**Important:** Whenever you register a model with django-reversion, run ``./manage.py createinitialrevisions`` command to populate the version database with an initial set of data. For large databases, this command can take a while to execute.

For more information about admin integration, please read the :ref:`admin integration <admin>` documentation.


Low-level API
-------------

You can use django-reversion's API to build version-controlled applications. For more information, please read the :ref:`API <api>` documentation.


More information
----------------

Installation
^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   django-versions
   migrations
   admin
   common-problems

Usage
^^^^^

.. toctree::
   :maxdepth: 1

   api
   commands
   signals
   how-it-works
   diffs
