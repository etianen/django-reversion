django-reversion
================

**django-reversion** is an extension to the Django web framework that provides
version control for model instances.

Features
--------

-  Roll back to any point in a model instance's history.
-  Recover deleted model instances.
-  Simple admin integration.


Documentation
-------------

Please read the `Getting Started <https://django-reversion.readthedocs.io/>`_
guide for more information.

Issue tracking and source code can be found at the
`main project website <http://github.com/etianen/django-reversion>`_.

You can keep up to date with the latest announcements by joining the
`django-reversion discussion group <http://groups.google.com/group/django-reversion>`_.


Upgrading
---------

Please check the `Changelog <https://github.com/etianen/django-reversion/blob/master/CHANGELOG.rst>`_ before upgrading
your installation of django-reversion.


Contributing
------------

Bug reports, bug fixes, and new features are always welcome. Please raise issues on the
`django-reversion project site <http://github.com/etianen/django-reversion>`_, and submit
pull requests for any new code.

You can run the test suite yourself from within a virtual environment with the following
commands. The test suite requires that both MySQL and PostgreSQL be installed.

.. code:: bash

    pip install 'tox>=2.3.1'
    tox

The django-reversion project is built on every push with `Travis CI <https://travis-ci.org/etianen/django-reversion>`_.

.. image:: https://travis-ci.org/etianen/django-reversion.svg?branch=master
    :target: https://travis-ci.org/etianen/django-reversion


Contributors
------------

The django-reversion project was developed by `Dave Hall <http://www.etianen.com/>`_ and contributed
to by `many other people <https://github.com/etianen/django-reversion/graphs/contributors>`_.
