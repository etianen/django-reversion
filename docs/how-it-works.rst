.. _how-it-works:

How it works
============

Saving Revisions
----------------

Enabling version control for a model is achieved using the ``reversion.register`` method. This registers the version control machinery with the ``post_save`` signal for that model, allowing new changes to the model to be caught.

::

    import reversion

    reversion.register(YourModel)

Any models that use subclasses of ``VersionAdmin`` in the admin interface will be automatically registered with django-reversion. As such, it is only necessary to manually register these models if you wish to override the default registration settings.

Whenever you save changes to a model, it is serialized using the Django serialization framework into a JSON string. This is saved to the database as a ``reversion.models.Version`` model. Each ``Version`` model is linked to a model instance using a ``GenericForeignKey``.

Foreign keys and many-to-many relationships are normally saved as their primary keys only. However, the ``reversion.register`` method takes an optional follow clause allowing these relationships to be automatically added to revisions. Please see :ref:`Low Level API <api>` for more information.

Reverting Versions
------------------

Reverting a version is simply a matter of loading the appropriate ``Version`` model from the database, deserializing the model data, and re-saving the old data.

There are a number of utility methods present on the ``Version`` object manager to assist this process. Please see :ref:`Low Level API <api>` for more information.

Revision Management
-------------------

Related changes to models are grouped together in revisions. This allows for atomic rollback from one revision to another. You can automate revision management using either ``reversion.middleware.RevisionMiddleware``, or the ``reversion.create_revision`` decorator.

For more information on creating revisions, please see :ref:`Low Level API <api>`.

Admin Integration
-----------------

Full admin integration is achieved using the ``reversion.admin.VersionAdmin`` class. This will create a new revision whenever a model is edited using the admin interface. Any models registered for version control, including inline models, will be included in this revision.

The ``object_history`` view is extended to make each ``LogEntry`` a link that can be used to revert the model back to the most recent version at the time the ``LogEntry`` was created.

Choosing to revert a model will display the standard model change form. The fields in this form are populated using the data contained in the revision corresponding to the chosen ``LogEntry``. Saving this form will result in a new revision being created containing the new model data.

For most projects, simply registering a model with a subclass of ``VersionAdmin`` is enough to satisfy all its version-control needs.
