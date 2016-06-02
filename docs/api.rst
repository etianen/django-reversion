.. _api:

Low-level API
=============

Use the django-reversion API to build version-controlled apps.


Basic usage
-----------

Registering models
^^^^^^^^^^^^^^^^^^

Models must be registered with django-reversion before they can be used with the API.

::

    import reversion

    reversion.register(YourModel)

**Note:** If you're using the :ref:`admin integration <admin>` for a model, registration is automatic.

**Important:** Whenever you register a model with django-reversion, run ``./manage.py createinitialrevisions`` command to populate the version database with an initial set of data. For large databases, this command can take a while to execute.

**Warning:** If you’re using django-reversion in a management command, and are using the automatic ``VersionAdmin`` registration method, you’ll need to import the relevant ``admin.py`` file at the top of your management command file.


Creating revisions
^^^^^^^^^^^^^^^^^^

A `revision` represents one or more changes made to your model instances, grouped together as a single unit. You create a revision by creating a `revision block`. When you call ``save()`` on a registered model inside a revision block, it will be added to that revision.

::

    with reversion.create_revision():
        obj = YourModel()
        obj.name = "obj v1"
        obj.save()
        # Store some meta-information.
        reversion.set_user(request.user)
        reversion.set_comment("Created revision 1")

    with reversion.create_revision():
        obj.name = "obj v2"
        obj.save()
        # Store some meta-information.
        reversion.set_user(request.user)
        reversion.set_comment("Created revision 2")


Loading versions
^^^^^^^^^^^^^^^^

Each model instance saved in a revision block is stored as a ``Version`` instance. You can load a ``Queryset`` of versions from the database. Versions are loaded with the most recent version first.

::

    versions = reversion.get_for_object(instance)
    assert len(versions) == 2

    assert versions[1].field_dict["name"] = "obj v1"
    assert versions[0].field_dict["name"] = "obj v2"


Accessing revisions
^^^^^^^^^^^^^^^^^^^

Each ``Version`` is associated with a ``Revision``. The ``Revision`` stores meta-information about the revision.

::

    assert versions[1].revision.comment = "Created revision 1"
    assert versions[1].revision.user = request.user
    assert isinstance(versions[1].revision.date_created, datetime.datetime)

    assert versions[0].revision.comment = "Created revision 2"
    assert versions[0].revision.user = request.user
    assert isinstance(versions[0].revision.date_created, datetime.datetime)

A ``Revision`` contains all the ``Version`` instances that were created in the revision block.

::

    assert versions[0].revision.version_set.count() == 1
    assert versions[0].revision.version_set.all()[0] == versions[0]

    assert versions[1].revision.version_set.count() == 1
    assert versions[1].revision.version_set.all()[0] == versions[1]


Reverting revisions
^^^^^^^^^^^^^^^^^^^

Revert a ``Revision`` to restore the contained model instances.

::

    versions[1].revision.revert()
    obj.refresh_from_db()
    assert obj.name == "version 1"

    versions[0].revision.revert()
    obj.refresh_from_db()
    assert obj.name == "version 2"


Restoring deleted model instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reverting a ``Revision`` will restore any contained model instances that have been deleted.

::

    pk = obj.pk
    obj.delete()

    versions[0].revision.revert()
    obj = YourModel.objects.get(pk=obj.pk)
    assert obj.name == "version 2"



API reference
-------------

Registering models
^^^^^^^^^^^^^^^^^^

Models must be registered with django-reversion before they can be used with the API.

``reversion.register(model_cls, **options)``

    Registers a model with django-reversion.

    By default, django-reversion will not register any parent classes of a model that uses multi-table inheritance. If you wish to also add parent models to your revision, you must explicitly add their ``parent_ptr`` fields to the follow parameter when you register the model.

    **Arguments:**

    - ``model_cls``: The Django model to register.
    - ``fields=None``: A tuple of fields to include in the serialized data. If ``None``, all fields will be included.
    - ``exclude=()``: A tuple of fields to exclude from the serialized data.
    - ``follow=()``: A tuple of model relationships to follow when saving a version of this model. ``ForeignKey``, ``ManyToManyField`` and reversion ``ForeignKey`` relationships are supported. Any property that returns a ``Model`` or ``QuerySet`` is also supported.
    - ``format="json"``: The name of a Django serialization format to use when saving the model instance.
    - ``for_concrete_model=True``: If `True` (default), then proxy models will be saved under the same content type as their concrete model. If `False`, then proxy models will be saved under their own content type, effectively giving proxy models their own distinct history.
    - ``signals=(post_save,)``: A tuple of Django signals that will trigger adding the model instance to an active revision.
    - ``eager_signals=()``: A tuple of Django signals that will trigger adding the model instance to an active revision. Unlike `signals`, model instances triggering this signal will


``reversion.is_registered(model_cls)``

    Returns whether the given model has been registered.

    **Arguments:**

    - ``model_cls``: The Django model to check.


``reversion.unregister(model_cls)``

    Unregisters the given model from django-reversion.

    **Arguments:**

    - ``model_cls``: The Django model to unregister.


``reversion.get_registered_models()``

    Returns an iterable of all registered models.


``reversion.get_adapter(model_cls)``

    Returns the ``VersionAdapter`` for the given ``model_cls``.

    **Arguments:**

    - ``model_cls``: The Django model to return the ``VersionAdapter`` for.


Creating revisions
^^^^^^^^^^^^^^^^^^

``reversion.create_revision(manage_manually=False, db=None)``

    Marks a block of code as a ``revision block``. Can also be used as a decorator. The revision block will be automatically wrapped in a ``transaction.atomic()``.

    **Arguments:**

    - ``manage_manually``: If ``True``, versions will not be saved when a model's ``save()`` method is called. This allows version control to be switched off for a given revision block.
    - ``db``: The database to save the version data into. The revision block will be wrapped in a transaction using this database. If ``None``, the default database for ``Revision`` models will be used.


``reversion.save_revision(objects=(), ignore_duplicates=False, user=None, comment="", meta=(), date_created=None, db=None)``

    Manually saves a revision without having to create a revision block and call `save()` on registered model instances.
    Returns the ``Revision`` that was created, or ``None`` if no revision was saved.

    **Arguments:**

    - ``objects``: An iterable of registered model instances to save in the revision.
    - ``ignore_duplicates``: If ``True``, the revision will only be saved if it's not a duplicate of a previous revision. **Note:** Checking for duplicate revisions adds significant overhead to the process of creating revisions. Don't enable it unless you really need it!
    - ``user``: A ``User`` model to add to the revision metadata.
    - ``comment``: A text comment to add to the revision metadata.
    - ``meta`: An iterable of unsaved model instances representing additional meta information about the revision. Each model must have a ``ForeignKey`` or ``OneToOneField`` to ``reversion.models.Revision``. When the revision is saved, all meta model instances will be saved in the same transaction.
    - ``date_created``: The date to associate with the revision. Defaults to ``django.utils.timezone.now()``.
    - ``db``: The database to save the revision into.


View helpers
^^^^^^^^^^^^

View helpers wrap every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a revision block. The request user will also be added to the revision metadata.

``reversion.views.create_revision()``

    Decorate a view with ``reversion.views.create_revision()`` to wrap the entire view in a revision block.


``reversion.views.RevisionMixin``

    Mixin a class-based view with ``reversion.views.RevisionMixin`` to wrap the entire view in a revision block.


``reversion.middleware.RevisionMiddleware``

    Use ``reversion.middleware.RevisionMiddleware`` to wrap every request in a revision block.

    To enable ``RevisionMiddleware``, add ``'reversion.middleware.RevisionMiddleware'`` to your ``MIDDLEWARE_CLASSES`` setting. For Django >= 1.10, add it to your ``MIDDLEWARE`` setting.

    **Warning**: This will wrap every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a database transaction. For best performance, consider marking individual views instead.


Version metadata
~~~~~~~~~~~~~~~~

Version metadata is saved to the revision when the outermost revision block ends.

``reversion.set_user(user)``

    Sets the user for the current revision.

    **Arguments:**

    - ``user``: A ``User`` model instance (or whatever your ``settings.AUTH_USER_MODEL`` references).


``reversion.get_user()``

    Gets the user for the current revision.


``reversion.set_comment(comment)``

    Sets the comment for the current revision.

    **Arguments:**

    - ``comment``: The text comment for the revision.


``reversion.get_comment()``

    Gets the comment for the current revision.


``reversion.add_meta(model_cls, **kwargs)``

    Adds custom metadata to a revision.

    **Arguments:**

    - ``model_cls``: A Django model to store the custom metadata. The model must have a ``ForeignKey`` or ``OneToOneField`` to ``reversion.models.Revision``.
    - ``**kwargs``: Values to be stored on the ``model_cls`` when it is saved.


Revision behavior
^^^^^^^^^^^^^^^^^

Revision behavior affects the entire outermost revision block, and is reset to default when the outermost revision block ends.

``reversion.set_ignore_duplicates(ignore_duplicates)``

    Sets whether duplicate revisions should be saved (default False).

    **Note:** Checking for duplicate revisions adds significant overhead to the process of creating revisions. Don't enable it unless you really need it!

    **Arguments:**

    - ``ignore_duplicates``: A ``bool`` indicating whether duplicate revisions should be saved.


``reversion.get_ignore_duplicates()``

    Gets whether duplicate revisions should be saved.


Loading versions
^^^^^^^^^^^^^^^^

All version loading methods return a ``VersionQuerySet`` of ``Version`` instances. You can further refine the result by filtering and ordering the queryset.

``reversion.get_for_object(obj, db=None)``

    Returns a ``Queryset`` of ``Version`` for the given model instance. The results are ordered with the most recent version first.

    **Arguments:**

    - ``obj``: An instance of a registered model.
    - ``db``: The database to load the versions from.


``reversion.get_for_object_reference(model_cls, pk, db=None)``

    Returns a ``Queryset`` of ``Version`` for the given model instance. The results are ordered with the most recent version first.

    **Arguments:**

    - ``model_cls``: A registered model class.
    - ``pk``: The primary key of an instance of the registered model class.
    - ``db``: The database to load the versions from.


``reversion.get_deleted(model_cls, db=None, model_db=None)``

    Returns a ``Queryset`` of ``Version`` for the given model where all versions represent a model instance that is no longer present in the database.

    **Arguments:**

    - ``model_cls``: A registered model class.
    - ``db``: The database to load the versions from.
    - ``model_db``: The database to check against for live model instances. Defaults to `db`.


``VersionQuerySet``
^^^^^^^^^^^^^^^^^^^

Querysets of ``Version`` models contain additional helper methods.

``VersionQuerySet.get_unique()``

    Returns an iterable of ``Version``, where each version is unique for a given database, model instance, and set of serialized fields.


``Version`` model
^^^^^^^^^^^^^^^^^

A ``Version`` instance represents a single model instance, serialized in a revision.

``Version.pk``

    The database primary key of the ``Version``.


``Version.revision``

    A ``ForeignKey`` to a ``Revision`` instance.


``Version.content_type``

    The ``ContentType`` of the serialized model instance.


``Version.object_id``

    The string representation of the serialized model instance's primary key.


``Version.db``

    The Django database alias where the serialized model was saved.


``Version.format``

    The name of the Django serialization format used to serialize the model instance.


``Version.serialized_data``

    The raw serialized data of the model instance.


``Version.object_repr``

    The stored snapshot of the model instance's ``__str__`` method when the instance was serialized.


``Version.field_dict``

    A dictionary of stored model fields. This includes fields from any parent models in the same revision.


``Version.revert()``

    Restores the serialized model instance to the database.


``Revision`` model
^^^^^^^^^^^^^^^^^^

A ``Revision`` model contains metadata about a revision, and groups together all ``Version`` instances created in that revision.

``Revision.pk``

    The database primary key of the ``Revision``.


``Revision.revision_manager``

    The ``RevisionManager`` used to save the revision.


``Revision.date_created``

    When the revision was created.


``Revision.user``

    The ``User`` that created the revision, or None.


``Revision.comment``

    A text comment on the revision.


``Revision.revert(delete=False)``

    Restores all contained serialized model instances to the database.

    **Arguments:**

    - ``delete``: If True, then any model instances which have been created and are reachable by the ``follow`` clause of any model instances in this revision will be deleted. This effectively restores a group of related models to the state they were in when the revision was created.
