django-reversion
================

**django-reversion** is an extension to the Django web framework that provides
comprehensive version control facilities.

Features
--------

*   Roll back to any point in a model's history - an unlimited undo facility!
*   Recover deleted models - never lose data again!
*   Admin integration for maximum usability.
*   Group related changes into revisions that can be rolled back in a single
    transaction.
*   Automatically save a new version whenever your model changes using Django's
    flexible signalling framework.
*   Automate your revision management with easy-to-use middleware.

**django-reversion** can be easily added to your existing Django project with an
absolute minimum of code changes.


Documentation
-------------

Please read the [Getting Started][] guide for more information.

[Getting Started]: https://github.com/etianen/django-reversion/wiki
    "Getting started with django-reversion"
    
Download instructions, bug reporting and links to full documentation can be
found at the [main project website][].

[main project website]: http://github.com/etianen/django-reversion
    "django-reversion on GitHub"

You can keep up to date with the latest announcements by joining the
[django-reversion discussion group][].

[django-reversion discussion group]: http://groups.google.com/group/django-reversion
    "django-reversion Google Group"


Upgrading
---------

If you're upgrading your existing installation of django-reversion, please check
the [Schema Migrations][] wiki page for information on any database changes and
how to upgrade. If you're using South to manage database migrations in your project,
then upgrading is as easy as running a few django management commands.

It's always worth checking the [CHANGELOG][] before upgrading too, just in case you
get caught off-guard my a minor upgrade to the library.

[Schema Migrations]: https://github.com/etianen/django-reversion/wiki/Schema-migrations
    "Schema Migrations for django-reversion"
[CHANGELOG]: https://github.com/etianen/django-reversion/blob/master/CHANGELOG.markdown
    "CHANGELOG for django-reversion"

    
More information
----------------

The django-reversion project was developed by Dave Hall. You can get the code
from the [django-reversion project site][].

[django-reversion project site]: http://github.com/etianen/django-reversion
    "django-reversion on GitHub"
    
Dave Hall is a freelance web developer, based in Cambridge, UK. You can usually
find him on the Internet in a number of different places:

*   [Website](http://www.etianen.com/ "Dave Hall's homepage")
*   [Blog](http://www.etianen.com/blog/developers/ "Dave Hall's blog")
*   [Twitter](http://twitter.com/etianen "Dave Hall on Twitter")
*   [Google Profile](http://www.google.com/profiles/david.etianen "Dave Hall's Google profile")