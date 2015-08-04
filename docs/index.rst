.. _index:

django-reversion documentation
==============================

Getting started with django-reversion
-------------------------------------

To install django-reversion, follow these steps:

1.  Install with pip: ``pip install django-reversion``.
2.  Add ``'reversion'`` to ``INSTALLED_APPS``.
3.  Run ``manage.py syncdb``.

The latest release (1.9.1) of django-reversion is designed to work with Django 1.8. If you have installed anything other than the latest version of Django, please check the :ref:`compatible Django versions <django-versions>` page before installing django-reversion.

There are a number of alternative methods you can use when installing django-reversion. Please check the :ref:`installation methods <installation>` page for more information.


Admin integration
-----------------

django-reversion can be used to add a powerful rollback and recovery facility to your admin site. To enable this, simply register your models with a subclass of ``reversion.VersionAdmin``::

    import reversion

    class YourModelAdmin(reversion.VersionAdmin):

        pass

    admin.site.register(YourModel, YourModelAdmin)

Whenever you register a model with the ``VersionAdmin`` class, be sure to run the ``./manage.py createinitialrevisions`` command to populate the version database with an initial set of model data. Depending on the number of rows in your database, this command could take a while to execute.

For more information about admin integration, please read the :ref:`admin integration <admin>` documentation.


Low Level API
-------------

You can use django-reversion's API to build powerful version-controlled views. For more information, please read the :ref:`low level API <api>` documentation.


More information
----------------

Installation
^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   installation
   django-versions
   migrations
   admin

Further reading
^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   api
   commands
   signals
   how-it-works
   diffs
