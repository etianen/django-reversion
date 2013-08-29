.. django-reversion documentation master file, created by
   sphinx-quickstart on Thu Aug 29 09:17:37 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _index:

django-reversion documentation
==============================

Getting started with django-reversion
-------------------------------------

To install django-reversion, follow these steps:

1.  Checkout the latest django-reversion release and copy or symlink the ``src/reversion`` directory into your ``PYTHONPATH``.
2.  Add ``'reversion'`` to your ``INSTALLED_APPS`` setting.
3.  Run the command ``manage.py syncdb``.

The latest release (1.7.1) of django-reversion is designed to work with Django 1.5. If you have installed anything other than the latest version of Django, please check the :ref:`compatible Django versions <compatible-django-versions>` page before downloading django-reversion.

There are a number of alternative methods you can use when installing django-reversion. Please check the :ref:`installation methods <installation-methods>` page for more information.


Admin integration
-----------------

django-reversion can be used to add a powerful rollback and recovery facility to your admin site. To enable this, simply register your models with a subclass of ``reversion.VersionAdmin``::

    import reversion

    class YourModelAdmin(reversion.VersionAdmin):

        pass
        
    admin.site.register(YourModel, YourModelAdmin)

Whenever you register a model with the ``VersionAdmin`` class, be sure to run the ``./manage.py createinitialrevisions`` command to populate the version database with an initial set of model data. Depending on the number of rows in your database, this command could take a while to execute.

For more information about admin integration, please visit the :ref:`admin integration <admin-integration>` wiki page.


Low Level API
-------------

You can use django-reversion's API to build powerful version-controlled views outside of the built-in admin site. For more information, please visit the :ref:`low level API <low-level-api>` wiki page.

More information
----------------

Installation
^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   installationmethods
   compatibledjangoversions
   schemamigrations
   adminintegration

Further reading
^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   lowlevelapi
   managementcommands
   signalssentbydjangoreversion
   howitworks
   generatingdiffs
