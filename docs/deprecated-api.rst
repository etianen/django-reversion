:orphan:

.. _deprecated-api:

Deprecated Low Level API
========================

For most projects, simply activating the admin integration will satisfy all your version-control needs. However, django-reversion comes with a lower-level API that allows you to manage versions within your own code.

Registering Models for Version Control
--------------------------------------

If you wish to use version control with a Django model, you must first register it with the version control machinery. If you have already registered the model with a subclass of ``VersionAdmin``, then this will have been done automatically. If not, then you must manually register the model as follows::

    import reversion

    reversion.register(YourModel)

A good place to do this is underneath the model definition, within your ``models.py`` file.

**Warning:** If you're using django-reversion in an management command, and are using the automatic ``VersionAdmin`` registration method, then you'll need to import the relevant admin.py file at the top of your management command file.

**Warning:** When Django starts up, some python scripts get loaded twice, which can cause 'already registered' errors to be thrown. If you place your calls to ``reversion.register`` in the ``models.py`` file, immediately after the model definition, this problem will go away.

Creating Revisions
------------------

A revision represents one or more changes made to your models, grouped together as a single unit. You create a revision by marking up a section of code to represent a revision. Whenever you call ``save()`` on a model within the scope of a revision, it will be added to that revision.

There are several ways to create revisions, as explained below. Although there is nothing stopping you from mixing and matching these approaches, it is recommended that you pick one of the methods and stick with it throughout your project.

Revision Middleware
^^^^^^^^^^^^^^^^^^^

Perhaps the simplest way to create revisions is to use ``reversion.middleware.RevisionMiddleware``. This will automatically wrap every request in a revision, ensuring that all changes to your models will be added to their version history.

To enable the revision middleware, simply add it to your ``MIDDLEWARE_CLASSES`` setting as follows::

    MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware', 
        'django.middleware.transaction.TransactionMiddleware',
        'reversion.middleware.RevisionMiddleware',
        # Other middleware goes here...
    )

Please note that ``RevisionMiddleware`` should go after ``TransactionMiddleware``. It is highly recommended that you use ``TransactionMiddleware`` in conjunction with ``RevisionMiddleware`` to ensure data integrity.

create_on_success Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need more control over revision management, you can decorate any function with the ``revision.create_on_success`` decorator. Any changes to your models that occur during this function will be grouped together into a revision.

::

    from reversion import revision

    @revision.create_on_success
    def your_view_func(request):
        """Changes to models will be saved in a revision."""
        your_model.save()

Revision Context Manager
^^^^^^^^^^^^^^^^^^^^^^^^

For Python 2.5 and above, you can also use a context manager to mark up a block of code. Once the block terminates, any changes made to your models will be grouped together into a revision.

::

    from __future__ import with_statement
    import reversion

    with reversion.revision:
        # Make changes to your models here.
        your_model.save()

Version meta data
-----------------

It is possible to attach a comment and a user reference to an active revision using the following method::

    @revision.create_on_success
    def your_view(request):
        your_model.save()
        # Set the revision meta data.
        revision.user = me
        revision.comment = "Doing some changes..."

If you use ``RevisionMiddleware``, then the user will automatically be added to the revision from the incoming request.

Custom meta data
^^^^^^^^^^^^^^^^

You can attach entirely custom meta data to a revision by creating a separate Django model to hold the additional fields. For example::

    class VersionRating(models.Model):
        revision = models.ForeignKey("reversion.Revision")  # This is required
        rating = models.PositiveIntegerField()

You can then attach this meta class to a revision using the following method::

    revision.add_meta(VersionRating, rating=5)

Reverting to previous revisions
-------------------------------

To revert a model to a previous version, use the following method::

    import datetime
    from reversion.models import Version
    from yoursite.models import YourModel

    your_model = YourModel.objects.get(pk=1)

    # Build a list of all previous versions, in order of creation:
    version_list = Version.objects.get_for_object(your_model)

    # Find the most recent version for a given date:
    version = Version.objects.get_for_date(your_model, datetime.datetime(2008, 7, 10))

    # Access the model data stored within the version:
    version_data = version.field_dict

    # Revert all objects in this revision:
    version.revision.revert()

    # Just revert this object, leaving the rest of the revision unchanged:
    version.revert()

Recovering Deleted Objects
--------------------------

To recover a deleted object, use the following method::

    from reversion.models import Version
    from yoursite.models import YourModel

    # Built a list of all deleted objects.
    deleted_list = Version.objects.get_deleted(YourModel)

    # Find the last version of an object before it was deleted:
    deleted_version = Version.objects.get_deleted_object(YourModel, object_id=1)

    # Recover all objects in this revision:
    deleted_version.revision.revert()

    # Just recover this object, leaving the rest of the revision unchanged:
    deleted_version.revert()

Transaction Management
----------------------

Reversion does not manage database transactions for you, as this is something that needs to be configured separately for the entire application. However, it is important that any revisions you create are themselves wrapped in a database transaction.

The easiest (and recommended) way to do this is by using the ``TransactionMiddleware`` supplied by Django. As noted above, this should go before the ``RevisionMiddleware``, if used.

If you want finer-grained control, then you should use the ``transaction.create_on_success`` decorator to wrap any functions where you will be creating revisions.

Advanced Model Registration
---------------------------

It is possible to customize how a model's data is saved to a revision by passing additional parameters to the ``reversion.register`` method. These are explained below.

Following foreign key relationships
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Normally, when you save a model it will only save the primary key of any ``ForeignKey`` or ``ManyToMany`` fields. If you also wish to include the data of the foreign key in your revisions, pass a list of relationship names to the ``reversion.register`` method.

::

    reversion.register(YourModel, follow=["your_foreign_key_field"])

**Please note:** If you use the follow parameter, you must also ensure that the related model has been registered with django-reversion.

In addition to ``ForeignKey`` and ``ManyToMany`` relationships, you can also specify related names of one-to-many relationships in the follow clause. For example, given the following database models::

    class Person(models.Model):
        pass

    class Pet(models.Model):
        person = models.ForeignKey(Person)

    reversion.register(Person, follow=["pet_set"])
    reversion.register(Pet)

Now whenever you save a revision containing a ``Person``, all related ``Pet`` instances will be automatically saved to the same revision.

Multi-table inheritance
^^^^^^^^^^^^^^^^^^^^^^^

By default, django-reversion will not save data in any parent classes of a model that uses multi-table inheritance. If you wish to also add parent models to your revision, you must explicitly add them to the follow clause when you register the model.

For example::

    class Place(models.Model):
        pass

    class Restaurant(Place):
        pass

    reversion.register(Place)
    reversion.register(Restaurant, follow=["place_ptr"])

Saving a subset of fields
-------------------------

If you only want a subset of fields to be saved to a revision, you can specify a fields argument to the register method.

::

    reversion.register(YourModel, fields=["pk", "foo", "bar"])

**Please note:** If you are not careful, then it is possible to specify a combination of fields that will make the model impossible to recover. As such, approach this option with caution.

Custom serialization format
^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, django-reversion will serialize model data using the 'json' serialization format. You can override this on a per-model basis using the format argument to the register method.

::

    reversion.register(YourModel, format="yaml")

**Please note:** The named serializer must serialize model data to a utf-8 encoded character string. Please verify that your serializer is compatible before using it with django-reversion.

Automatic Registration by the Admin Interface
---------------------------------------------

As mentioned at the start of this page, the admin interface will automatically register any models that use the ``VersionAdmin`` class. The admin interface will automatically follow any ``InlineAdmin`` relationships, as well as any parent links for models that use multi-table inheritance.

For example::

    # models.py

    class Place(models.Model):
        pass

    class Restaurant(Place):
        pass

    class Meal(models.Model):
        restaurant = models.ForeignKey(Restaurant)

    # admin.py

    class MealInlineAdmin(admin.StackedInline):
        model = Meal

    class RestaurantAdmin(VersionAdmin):
        inline = MealInlineAdmin,

    admin.site.register(Restaurant, RestaurantAdmin)

Since ``Restaurant`` has been registered with a subclass of ``VersionAdmin``, the following registration calls will be made automatically::

    reversion.register(Place)
    reversion.register(Restaurant, follow=["place_ptr", "meal_set"])
    reversion.register(Meal)

As such, it is only necessary to manually register these models if you wish to override the default registration parameters. In most cases, however, the defaults will suit just fine.
