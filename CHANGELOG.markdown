django-reversion changelog
==========================

1.4 - 27/04/2011
----------------

* Added in a version flag for add / change / delete annotations.
* Added experimental deleterevisions management command.
* Added a --comment option to createinitialrevisions management command.
* Django 1.3 compatibility.


1.3.3 - 05/03/2011
------------------

* Improved resilience of revert() to database integrity errors.
* Added in Czech translation.
* Added ability to only save revisions if there is no change.
* Fixed long-running bug with file fields in inline related admin models.
* Easier debugging for createinitialrevisions command.
* Improved compatibility with Oracle database backend.
* Fixed error in MySQL tests.
* Greatly improved performance of get_deleted() Version manager method.
* Fixed an edge-case UnicodeError.


1.3.2 - 22/10/2010
------------------

*   Added Polish translation.
*   Added French translation.
*   Improved resilience of unit tests.
*   Improved scaleability of Version.object.get_deleted() method.
*   Improved scaleability of createinitialrevisions command.
*   Removed post_syncdb hook.
*   Added new createinitialrevisions management command.
*   Fixed DoesNotExistError with OneToOneFields and follow.


1.3.1 - 31/05/2010
------------------

This release is compatible with Django 1.2.1.

*   Django 1.2.1 admin compatibility.


1.2.1 - 03/03/2010
------------------

This release is compatible with Django 1.1.1.

*   The django syncdb command will now automatically populate any
    version-controlled models with an initial revision. This ensures existing 
    projects that integrate Reversion won't get caught out. 
*   Reversion now works with SQLite for tables over 999 rows. 
*   Added Hebrew translation. 


1.2 - 12/10/2009
----------------

This release is compatible with Django 1.1.

*   Django 1.1 admin compatibility.


1.1.2 - 23/07/2009
------------------

This release is compatible with Django 1.0.4.

*   Doc tests. 
*   German translation update. 
*   Better compatibility with the Django trunk.  
*   The ability to specify a serialization format used by the  ReversionAdmin
    class when models are auto-registered. 
*   Reduction in the number of database queries performed by the Reversion   
    admin interface.
     
     
1.1.1 - 25/03/2010
------------------

This release is compatible with Django 1.0.2.

*   German and Italian translations. 
*   Helper functions for generating diffs. 
*   Improved handling of one-to-many relationships in the admin.