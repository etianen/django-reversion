.. _changelog:

django-reversion changelog
==========================

2.0.9 - 19/06/2017
------------------

- Bugfix: Deleted inline admin instances no longer added to revision.
- Bugfix: M2M relations correctly added to revision (@etianen, @claudep).
- Improved performance of 0003 migration (@mkurek).
- Documentation improvements (@orlra, @guettli, @meilinger).
- Django 1.11 support (@claudep).
- Added ``atomic=True`` parameter to ``create_revision`` (Ernesto Ferro).


2.0.8 - 28/11/2016
------------------

- Setting ``revision.user`` in ``process_response`` for middleware (@etianen).
- Fixing localization of model primary keys in `recover_list.html` (@w4rri0r3k).
- Documentation tweaks (@jaywink).


2.0.7 - 31/10/2016
------------------

- Database migrations now db-aware (@alukach).
- Added "revert" and "recover" context variables to admin templates (@kezabelle).
- Added ``post_revision_commit`` and ``pre_revision_commit`` signals back in (@carlosxl).
- Fixing datetime in admin change message (@arogachev).
- Fixing performance bug in postgres (@st4lk).
- Fixing admin change messages in Django 1.10+ (@claudep).
- Fixing revision middleware behavior in Django 1.10+ (@etianen).
- Documentation tweaks (@jschneier).
- Deprecation fixes (@KhasanovBI, @zsiciarz, @claudep).
- Releasing as a universal wheel (@adamchainz).


2.0.6 - 21/07/2016
------------------

- Fixed ``RevisionMiddleware`` always rolling back transactions in gunicorn (@stebunovd, @etianen).
- Tweaks and minor bugfixes (@SahilMak).


2.0.5 - 29/06/2016
------------------

- Fixed LookupError when running migration 0003 with stale content types (@etianen).


2.0.4 - 20/06/2016
------------------

- Fixed LookupError when running migration 0003 (@etianen).
- Fixed duplicate versions using ``get_deleted()`` (@etianen).
- Fixed unexpected deletion of underflowing revisions when using ``--keep`` switch with ``deleterevisions`` (@etianen).


2.0.3 - 14/06/2016
------------------

- Added support for m2m fields with a custom ``through`` model (@etianen).


2.0.2 - 13/06/2016
------------------

- Fixing migration 0003 in MySQL (@etianen).


2.0.1 - 13/06/2016
------------------

- Improved performance of migration 0003 (@BertrandBordage).
- De-duplicating ``Version`` table before applying migration 0004 (@BertrandBordage, @etianen).


2.0.0 - 11/06/2016
------------------

django-reversion was first released in May 2008, and has been in active development ever since. Over this time it's developed a certain amount of cruft from legacy and unused features, resulting in needless complexity and multiple ways of achieving the same task.

This release substantially cleans and refactors the codebase. Much of the top-level functionality remains unchanged or is very similar. The release notes are divided into subsections to make it easier to find out where you need to update your code.

This release includes a migration for the ``Version`` model that may take some time to complete.


General improvements
^^^^^^^^^^^^^^^^^^^^

* Dramatically improved performance of version lookup for models with a non-integer primary key (@etianen, @mshannon1123).
* Documentation refactor (@etianen).
* Test refactor (@etianen).
* Minor tweaks and bugfixes (@etianen, @bmarika, @ticosax).


Admin
^^^^^

* Fixed issue with empty revisions being created in combination with ``RevisionMiddleware`` (@etianen).

* **Breaking:** Removed ``reversion_format`` property from ``VersionAdmin`` (@etianen).

    Use ``VersionAdmin.reversion_register`` instead.

    .. code::

        class YourVersionAdmin(VersionAdmin):

            def reversion_register(self, model, **options):
                options["format"] = "yaml"
                super(YourVersionAdmin, self).reversion_register(model, **options)

* **Breaking:** Removed ``ignore_duplicate_revisions`` property from ``VersionAdmin`` (@etianen).

    Use ``VersionAdmin.reversion_register`` instead.

    .. code::

        class YourVersionAdmin(VersionAdmin):

            def reversion_register(self, model, **options):
                options["ignore_duplicate_revisions"] = True
                super(YourVersionAdmin, self).reversion_register(model, **options)




Management commands
^^^^^^^^^^^^^^^^^^^

* **Breaking:** Refactored arguments to ``createinitialrevisions`` (@etianen).

    All existing functionality should still be supported, but several parameter names have been updated to match Django coding conventions.

    Check the command ``--help`` for details.

* **Breaking:** Refactored arguments to ``deleterevisions`` (@etianen).

    All existing functionality should still be supported, but several parameter names have been updated to match Django coding conventions, and some duplicate parameters have been removed. The confirmation prompt has been removed entirely, and the command now always runs in the ``--force`` mode from the previous version.

    Check the command ``--help`` for details.


Middleware
^^^^^^^^^^

* Added support for using ``RevisionMiddleware`` with new-style Django 1.10 ``MIDDLEWARE`` (@etianen).
* Middleware wraps entire request in ``transaction.atomic()`` to preserve transactional integrity of revision and models (@etianen).


View helpers
^^^^^^^^^^^^

* Added ``reversion.views.create_revision`` view decorator (@etianen).
* Added ``reversion.views.RevisionMixin`` class-based view mixin (@etianen).


Low-level API
^^^^^^^^^^^^^

* Restored many of the django-reversion API methods back to the top-level namespace (@etianen).
* Revision blocks are now automatically wrapped in ``transaction.atomic()`` (@etianen).
* Added ``for_concrete_model`` argument to ``reversion.register()`` (@etianen).
* Added ``Version.objects.get_for_model()`` lookup function (@etianen).
* Added ``reversion.add_to_revision()`` for manually adding model instances to an active revision (@etianen).
* Removed ``Version.object_id_int`` field, in favor of a unified ``Version.object_id`` field for all primary key types (@etianen).

* **Breaking:** ``reversion.get_for_object_reference()`` has been moved to ``Version.objects.get_for_object_reference()`` (@etianen).

* **Breaking:** ``reversion.get_for_object()`` has been moved to ``Version.objects.get_for_object()`` (@etianen).

* **Breaking:** ``reversion.get_deleted()`` has been moved to ``Version.objects.get_deleted()`` (@etianen).

* **Breaking:** ``Version.object_version`` has been renamed to ``Version._object_version`` (@etianen).

* **Breaking:** Refactored multi-db support (@etianen).

    django-reversion now supports restoring model instances to their original database automatically. Several parameter names have also be updated to match Django coding conventions.

    If you made use of the previous multi-db functionality, check the latest docs for details. Otherwise, everything should *just work*.

* **Breaking:** Removed ``get_ignore_duplicates`` and ``set_ignore_duplicates`` (@etianen).

    ``ignore_duplicates`` is now set in reversion.register() on a per-model basis.

* **Breaking:** Removed ``get_for_date()`` function (@etianen).

    Use ``get_for_object().filter(revision__date_created__lte=date)`` instead.

* **Breaking:** Removed ``get_unique_for_object()`` function (@etianen).

    Use ``get_for_object().get_unique()`` instead.

* **Breaking:** Removed ``signal`` and ``eager_signals`` argument from ``reversion.register()`` (@etianen).

    To create revisions on signals other than ``post_save`` and ``m2m_changed``, call ``reversion.add_to_revision()`` in a signal handler for the appropriate signal.

    .. code:: python

        from django.dispatch import receiver
        import reversion
        from your_app import your_custom_signal

        @reciever(your_custom_signal)
        def your_custom_signal_handler(instance, **kwargs):
            if reversion.is_active():
                reversion.add_to_revision(instance)

    This approach will work for both eager and non-eager signals.

* **Breaking:** Removed ``adapter_cls`` argument from ``reversion.register()`` (@etianen).

* **Breaking:** Removed ``reversion.save_revision()`` (@etianen).

    Use reversion.add_to_revision() instead.

    .. code:: python

        import reversion

        with reversion.create_revision():
            reversion.add_to_revision(your_obj)


Signals
^^^^^^^

* **Breaking:** Removed ``pre_revision_commit`` signal (@etianen).

    Use the Django standard ``pre_save`` signal for ``Revision`` instead.

* **Breaking:** Removed ``post_revision_commit`` signal (@etianen).

    Use the Django standard ``post_save`` signal for ``Revision`` instead.


Helpers
^^^^^^^

* **Breaking:** Removed ``patch_admin`` function (@etianen).

    Use ``VersionAdmin`` as a mixin to 3rd party ModelAdmins instead.

    .. code::

        @admin.register(SomeModel)
        class YourModelAdmin(VersionAdmin, SomeModelAdmin):

            pass

* **Breaking:** Removed ``generate_diffs`` function (@etianen).

    django-reversion no supports an official diff helper. There are much better ways of achieving this now, such as `django-reversion-compare <https://github.com/jedie/django-reversion-compare>`_.

    The old implementation is available for reference from the `previous release <https://github.com/etianen/django-reversion/blob/release-1.10.2/src/reversion/helpers.py>`_.

* **Breaking:** Removed ``generate_patch`` function (@etianen).

    django-reversion no supports an official diff helper. There are much better ways of achieving this now, such as `django-reversion-compare <https://github.com/jedie/django-reversion-compare>`_.

    The old implementation is available for reference from the `previous release <https://github.com/etianen/django-reversion/blob/release-1.10.2/src/reversion/helpers.py>`_.

* **Breaking:** Removed ``generate_patch_html`` function (@etianen).

    django-reversion no supports an official diff helper. There are much better ways of achieving this now, such as `django-reversion-compare <https://github.com/jedie/django-reversion-compare>`_.

    The old implementation is available for reference from the `previous release <https://github.com/etianen/django-reversion/blob/release-1.10.2/src/reversion/helpers.py>`_.

Models
^^^^^^

* **Breaking:** Ordering of ``-pk`` added to models ``Revision`` and ``Version``. Previous was the default ``pk``.

1.10.2 - 18/04/2016
-------------------

* Fixing deprecation warnings (@claudep).
* Minor tweaks and bug fixes (@fladi, @claudep, @etianen).


1.10.1 - 27/01/2016
-------------------

* Fixing some deprecation warnings (@ticosax).
* Minor tweaks (@claudep, @etianen).


1.10 - 02/12/2015
-----------------

* **Breaking:** Updated the location of ``VersionAdmin``.

    Prior to this change, you could access the ``VersionAdmin`` class using the following import:

    .. code:: python

        # Old-style import for accessing the admin class.
        import reversion

        # Access admin class from the reversion namespace.
        class YourModelAdmin(reversion.VersionAdmin):

            pass

    In order to support Django 1.9, the admin class has been moved to the following
    import:

    .. code:: python

        # New-style import for accesssing admin class.
        from reversion.admin import VersionAdmin

        # Use the admin class directly.
        class YourModelAdmin(VersionAdmin):

            pass

* **Breaking:** Updated the location of low-level API methods.
    Prior to this change, you could access the low-level API using the following import:

    .. code:: python

        # Old-style import for accessing the low-level API.
        import reversion

        # Use low-level API methods from the reversion namespace.
        @reversion.register
        class YourModel(models.Model):

            pass

    In order to support Django 1.9, the low-level API
    methods have been moved to the following import:

    .. code:: python

        # New-style import for accesssing the low-level API.
        from reversion import revisions as reversion

        # Use low-level API methods from the revisions namespace.
        @reversion.register
        class YourModel(models.Model):

            pass

* **Breaking:** Updated the location of http://django-reversion.readthedocs.org/en/latest/signals.html.
    Prior to this change, you could access the reversion signals using the following import:

    .. code:: python

        # Old-style import for accessing the reversion signals
        import reversion

        # Use signals from the reversion namespace.
        reversion.post_revision_commit.connect(...)

    In order to support Django 1.9, the reversion signals have been moved to the following
    import:

    .. code:: python

        # New-style import for accesssing the reversion signals.
        from reversion.signals import pre_revision_commit, post_revision_commit

        # Use reversion signals directly.
        post_revision_commit.connect(...)

* Django 1.9 compatibility (@etianen).
* Added spanish (argentina) translation (@gonzalobustos).
* Minor bugfixes and tweaks (@Blitzstok, @IanLee1521, @lutoma, @siamalekpour, @etianen).


1.9.3 - 07/08/2015
------------------

* Fixing regression with admin redirects following save action (@etianen).


1.9.2 - 07/08/2015
------------------

* Fixing regression with "delete", "save as new" and "save and continue" button being shown in recover and revision admin views (@etianen).
* Fixing regression where VersionAdmin.ignore_duplicate_revisions was ignored (@etianen).


1.9.1 - 04/08/2015
------------------

* Fixing packaging error that rendered the 1.9.0 release unusable. No way to cover up the mistake, so here's a brand new bugfix release! (@etianen).


1.9.0 - 04/08/2015
------------------

* Using database transactions do render consistent views of past revisions in database admin, fixing a lot of lingering minor issues (@etianen).
* Correct handling of readonly fields in admin (@etianen).
* Updates to Czech translation (@cuchac).
* Arabic translation (@RamezIssac).
* Fixing deleterevisions to work with Python2 (@jmurty).
* Fixing edge-cases where an object does not have a PK (@johnfraney).
* Tweaks, code cleanups and documentation fixes (@claudep, @johnfraney, @podloucky-init, Drew Hubl, @JanMalte, @jmurty, @etianen).


1.8.7 - 21/05/2015
------------------

* Fixing deleterevisions command on Python 3 (@davidfsmith).
* Fixing Django 1.6 compatibility (@etianen).
* Removing some Django 1.9 deprecation warnings (@BATCOH, @niknokseyer).
* Minor tweaks (@nikolas, @etianen).


1.8.6 - 13/04/2015
------------------

* Support for MySQL utf8mb4 (@alexhayes).
* Fixing some Django deprecation warnings (Drew Hubl, @khakulov, @adonm).
* Versions passed through by reversion.post_revision_commit now contain a primary key (@joelarson).


1.8.5 - 31/10/2014
------------------

* Added support for proxy models (@AgDude, @bourivouh).
* Allowing registration of models with django-reversion using custom signals (@ErwinJunge).
* Fixing some Django deprecation warnings (@skipp, @narrowfail).


1.8.4 - 07/09/2014
------------------

* Fixing including legacy south migrations in PyPi package (@GeyseR).


1.8.3 - 06/09/2014
------------------

* Provisional Django 1.7 support (@etianen).
* Multi-db and multi-manager support to management commands (@marekmalek).
* Added index on reversion.date_created (@rkojedzinszky).
* Minor bugfixes and documentation improvements (@coagulant).


1.8.2 - 01/08/2014
------------------

* reversion.register() can now be used as a class decorator (@aquavitae).
* Danish translation (@Vandborg).
* Improvements to Travis CI integration (@thedrow).
* Simplified Chinese translation (@QuantumGhost).
* Minor bugfixes and documentation improvements (@marekmalek, @dhoffman34, @mauricioabreu, @mark0978).


1.8.1 - 29/05/2014
------------------

* Slovak translation (@jbub).
* Deleting a user no longer deletes the associated revisions (@daaray).
* Improving handling of inline models in admin integration (@blueyed).
* Improving error messages for proxy model registration (@blueyed).
* Improvements to using migrations with custom user model (@aivins).
* Removing sys.exit() in deleterevisions management command, allowing it to be used internally by Django projects (@tongwang).
* Fixing some backwards-compatible admin deprecation warnings (Thomas Schreiber).
* Fixing tests if RevisionMiddleware is used as a decorator in the parent project (@jmoldow).
* Derived models, such as those generated by deferred querysets, now work.
* Removed deprecated low-level API methods.


1.8.0 - 01/11/2013
------------------

* Django 1.6 compatibility (@niwibe & @meshy).
* Removing type flag from Version model.
* Using bulk_create to speed up revision creation.
* Including docs in source distribution (@pquentin & @fladi).
* Spanish translation (@alexander-ae).
* Fixing edge-case bugs in revision middleware (@pricem & @oppianmatt).


1.7.1 - 26/06/2013
------------------

*  Bugfixes when using a custom User model.
*  Minor bugfixes.


1.7 - 27/02/2013
----------------

*  Django 1.5 compatibility.
*  Experimantal Python 3.3 compatibility!


1.6.6 - 12/02/2013
------------------

*  Removing version checking code. It's more trouble than it's worth.
*  Dutch translation improvements.


1.6.5 - 12/12/2012
------------------

*  Support for Django 1.4.3.


1.6.4 - 28/10/2012
------------------

*  Support for Django 1.4.2.


1.6.3 - 05/09/2012
------------------

*  Fixing issue with reverting models with unique constraints in the admin.
*  Enforcing permissions in admin views.


1.6.2 - 31/07/2012
------------------

*  Batch saving option in createinitialrevisions.
*  Suppressing warning for Django 1.4.1.


1.6.1 - 20/06/2012
------------------

*  Swedish translation.
*  Fixing formating for PyPi readme and license.
*  Minor features and bugfixes.


1.6 - 27/03/2012
----------------

*  Django 1.4 compatibility.


1.5.2 - 27/03/2012
------------------

*  Multi-db support.
*  Brazillian Portuguese translation.
*  New manage_manually revision mode.


1.5.1 - 20/10/2011
-------------------

*  Polish translation.
*  Minor bug fixes.


1.5 - 04/09/2011
----------------

*  Added in simplified low level API methods, and deprecated old low level API methods.
*  Added in support for multiple revision managers running in the same project.
*  Added in significant speedups for models with integer primary keys.
*  Added in cleanup improvements to patch generation helpers.
*  Minor bug fixes.


1.4 - 27/04/2011
----------------

*  Added in a version flag for add / change / delete annotations.
*  Added experimental deleterevisions management command.
*  Added a --comment option to createinitialrevisions management command.
*  Django 1.3 compatibility.


1.3.3 - 05/03/2011
------------------

*  Improved resilience of revert() to database integrity errors.
*  Added in Czech translation.
*  Added ability to only save revisions if there is no change.
*  Fixed long-running bug with file fields in inline related admin models.
*  Easier debugging for createinitialrevisions command.
*  Improved compatibility with Oracle database backend.
*  Fixed error in MySQL tests.
*  Greatly improved performance of get_deleted() Version manager method.
*  Fixed an edge-case UnicodeError.


1.3.2 - 22/10/2010
------------------

*  Added Polish translation.
*  Added French translation.
*  Improved resilience of unit tests.
*  Improved scaleability of Version.object.get_deleted() method.
*  Improved scaleability of createinitialrevisions command.
*  Removed post_syncdb hook.
*  Added new createinitialrevisions management command.
*  Fixed DoesNotExistError with OneToOneFields and follow.


1.3.1 - 31/05/2010
------------------

This release is compatible with Django 1.2.1.

*  Django 1.2.1 admin compatibility.


1.2.1 - 03/03/2010
------------------

This release is compatible with Django 1.1.1.

*  The django syncdb command will now automatically populate any
   version-controlled models with an initial revision. This ensures existing
   projects that integrate Reversion won't get caught out.
*  Reversion now works with SQLite for tables over 999 rows.
*  Added Hebrew translation.


1.2 - 12/10/2009
----------------

This release is compatible with Django 1.1.

*  Django 1.1 admin compatibility.


1.1.2 - 23/07/2009
------------------

This release is compatible with Django 1.0.4.

*  Doc tests.
*  German translation update.
*  Better compatibility with the Django trunk.
*  The ability to specify a serialization format used by the  ReversionAdmin
   class when models are auto-registered.
*  Reduction in the number of database queries performed by the Reversion
*  admin interface.


1.1.1 - 25/03/2010
------------------

This release is compatible with Django 1.0.2.

*  German and Italian translations.
*  Helper functions for generating diffs.
*  Improved handling of one-to-many relationships in the admin.
