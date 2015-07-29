django-reversion
================

**django-reversion** is an extension to the Django web framework that provides
comprehensive version control facilities.

Features
--------

-  Roll back to any point in a model's history - an unlimited undo facility!
-  Recover deleted models - never lose data again!
-  Admin integration for maximum usability.
-  Group related changes into revisions that can be rolled back in a single
   transaction.
-  Automatically save a new version whenever your model changes using Django's
   flexible signalling framework.
-  Automate your revision management with easy-to-use middleware.

**django-reversion** can be easily added to your existing Django project with an
absolute minimum of code changes.


Documentation
-------------

Please read the `Getting Started <http://django-reversion.readthedocs.org/en/latest/>`_
guide for more information.
    
Download instructions, bug reporting and links to full documentation can be
found at the `main project website <http://github.com/etianen/django-reversion>`_.

You can keep up to date with the latest announcements by joining the
`django-reversion discussion group <http://groups.google.com/group/django-reversion>`_.


Upgrading
---------

If you're upgrading your existing installation of django-reversion, please check
the `Schema Migrations <http://django-reversion.readthedocs.org/en/latest/migrations.html>`_
documentation for information on any database changes and how to upgrade. If you're using
South to manage database migrations in your project, then upgrading is as easy as running
a few django management commands.

It's always worth checking the `CHANGELOG <https://github.com/etianen/django-reversion/blob/master/CHANGELOG.rst>`_
before upgrading too, just in case you get caught off-guard by a minor upgrade to the library.


Contributing
------------

Bug reports, bug fixes, and new features are always welcome. Please raise issues on the
`django-reversion project site <http://github.com/etianen/django-reversion>`_, and submit
pull requests for any new code.

You can run the test suite yourself from within a virtual environment with the following
commands:

::

    $ pip install -e .[test]
    $ coverage run src/tests/manage.py test src/tests/test_reversion/

The django-reversion project is built on every push with `Travis CI <https://travis-ci.org/etianen/django-reversion>`_.

.. image:: https://travis-ci.org/etianen/django-reversion.svg?branch=master
    :target: https://travis-ci.org/etianen/django-reversion

    
More information
----------------

The django-reversion project was developed by Dave Hall. You can get the code
from the `django-reversion project site <http://github.com/etianen/django-reversion>`_.
    
Dave Hall is a freelance web developer, based in Cambridge, UK. You can usually
find him on the Internet in a number of different places:

-  `Website <http://www.etianen.com/>`_
-  `Twitter <http://twitter.com/etianen>`_
-  `Google Profile <http://www.google.com/profiles/david.etianen>`_
