.. _installation:

Installation methods
====================

**Note:** It is recommended that you always use the latest release of django-reversion with the latest release of Django. If you are using an older version of Django, then please check out the :ref:`Compatible Django Versions <compatible-django-versions>` page for more information.

Project download area
---------------------

All releases of django-reversion are available in the `project downloads area <https://github.com/etianen/django-reversion/tags>`_. Simply copy or symlink the `src/reversion` directory into your `PYTHONPATH`, and you're good to go!

Git
---

Using Git to install django-reversion provides an easy way of upgrading your installation at a later date. Simply clone the `public git repository <http://github.com/etianen/django-reversion>`_ and symlink the ``src/reversion`` directory into your ``PYTHONPATH``::

    $ git clone git://github.com/etianen/django-reversion.git
    $ cd django-reversion.git
    $ git checkout release-1.7.1
    $ ln -s src/reversion /your/pythonpath/location/reversion

easy_install
------------

The popular easy_install utility can be used to install the latest django-reversion release from the Python Package Index. Simply run the following command in a terminal::

    $ sudo easy_install django-reversion
