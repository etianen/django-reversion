.. _api:

django-reversion API
====================

Use the django-reversion API to build version-controlled apps. See also :ref:`Views` and :ref:`Middleware`.


Overview
--------

Registering models
^^^^^^^^^^^^^^^^^^

Models must be registered with django-reversion before they can be used with the API.

.. code:: python

    from django.db import models
    import reversion

    @reversion.register()
    class YourModel(models.Model):

        pass

.. Hint::
    If you're using the :ref:`admin`, model registration is automatic. If you’re using django-reversion in a management command, make sure you call ``django.contrib.admin.autodiscover`` to load the admin modules before using the django-reversion API.

.. include:: /_include/post-register.rst


Creating revisions
^^^^^^^^^^^^^^^^^^

A *revision* represents one or more changes made to your model instances, grouped together as a single unit. You create a revision by creating a *revision block*. When you call ``save()`` on a registered model inside a revision block, it will be added to that revision.

.. code:: python

    # Declare a revision block.
    with reversion.create_revision():

        # Save a new model instance.
        obj = YourModel()
        obj.name = "obj v1"
        obj.save()

        # Store some meta-information.
        reversion.set_user(request.user)
        reversion.set_comment("Created revision 1")

    # Declare a new revision block.
    with reversion.create_revision():

        # Update the model instance.
        obj.name = "obj v2"
        obj.save()

        # Store some meta-information.
        reversion.set_user(request.user)
        reversion.set_comment("Created revision 2")

.. Important::

    Bulk actions, such as ``Queryset.update()``, do not send signals, so won't be noticed by django-reversion.


Loading revisions
^^^^^^^^^^^^^^^^^

Each model instance saved in a revision block is serialized as a :ref:`Version`. All versions in a revision block are associated with a single :ref:`Revision`.

You can load a ``Queryset`` of versions from the database. Versions are loaded with the most recent version first.

.. code:: python

    # Load a queryset of versions for a specific model instance.
    versions = reversion.get_for_object(instance)
    assert len(versions) == 2

    # Check the serialized data for the first version.
    assert versions[1].field_dict["name"] = "obj v1"

    # Check the serialized data for the second version.
    assert versions[0].field_dict["name"] = "obj v2"


Revision metadata
^^^^^^^^^^^^^^^^^

:ref:`Revision` stores meta-information about the revision.

.. code:: python

    # Check the revision metadata for the first revision.
    assert versions[1].revision.comment = "Created revision 1"
    assert versions[1].revision.user = request.user
    assert isinstance(versions[1].revision.date_created, datetime.datetime)

    # Check the revision metadata for the second revision.
    assert versions[0].revision.comment = "Created revision 2"
    assert versions[0].revision.user = request.user
    assert isinstance(versions[0].revision.date_created, datetime.datetime)


Reverting revisions
^^^^^^^^^^^^^^^^^^^

Revert a :ref:`Revision` to restore the serialized model instances.

.. code:: python

    # Revert the first revision.
    versions[1].revision.revert()

    # Check the model instance has been reverted.
    obj.refresh_from_db()
    assert obj.name == "version 1"

    # Revert the second revision.
    versions[0].revision.revert()

    # Check the model instance has been reverted.
    obj.refresh_from_db()
    assert obj.name == "version 2"


Restoring deleted model instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reverting a :ref:`Revision` will restore any serialized model instances that have been deleted.

.. code:: python

    # Delete the model instance, but store the pk.
    pk = obj.pk
    obj.delete()

    # Revert the second revision.
    versions[0].revision.revert()

    # Check the model has been restored to the database.
    obj = YourModel.objects.get(pk=obj.pk)
    assert obj.name == "version 2"


.. _registration-api:

Registration API
----------------

.. _register:

reversion.register(model, \*\*options)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Registers a model with django-reversion.

Throws :ref:`RegistrationError` if the model has already been registered.

``model``
    The Django model to register.

``fields=None``
    An iterable of field names to include in the serialized data. If ``None``, all fields will be included.

``exclude=()``
    An iterable of field names to exclude from the serialized data.

``follow=()``
    An iterable of model relationships to follow when saving a version of this model. ``ForeignKey``, ``ManyToManyField`` and reversion ``ForeignKey`` relationships are supported. Any property that returns a ``Model`` or ``QuerySet`` is also supported.

``format="json"``
    The name of a Django serialization format to use when saving the model instance.

``for_concrete_model=True``
    If ``True`` proxy models will be saved under the same content type as their concrete model. If ``False``, proxy models will be saved under their own content type, effectively giving proxy models their own distinct history.

``signals=(post_save,)``
    An iterable of Django signals that will trigger adding the model instance to an active revision.

``eager_signals=()``
    An iterable of Django signals that will trigger adding the model instance to an active revision. Unlike ``signals``, model instances triggering this signal will be serialized immediately, rather than at the end of the revision block. This makes it suitable for usage with signals like ``pre_delete``.

``adapter_cls=reversion.VersionAdapter``
    A subclass of :ref:`VersionAdapter` to use to register the model.

.. Hint::
    By default, django-reversion will not register any parent classes of a model that uses multi-table inheritance. If you wish to also add parent models to your revision, you must explicitly add their ``parent_ptr`` fields to the ``follow`` parameter when you register the model.

.. include:: /_include/post-register.rst


reversion.is_registered(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns whether the given model has been registered with django-reversion.

``model``
    The Django model to check.


reversion.unregister(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Unregisters the given model from django-reversion.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    The Django model to unregister.


reversion.get_registered_models()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of all registered models.


reversion.get_adapter(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the :ref:`VersionAdapter` for the given model.

``model``
    The Django model look up.


.. _revision-api:

Revision API
------------

reversion.create_revision(manage_manually=False, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Marks a block of code as a *revision block*. Can also be used as a decorator. The revision block will be wrapped in a ``transaction.atomic()``.

.. include:: /_include/create-revision-args.rst


reversion.set_ignore_duplicates(ignore_duplicates)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: /_include/ignore-duplicates.rst

Throws :ref:`RevisionManagementError` if there is no active revision block.

``ignore_duplicates``
    A ``bool`` indicating whether duplicate revisions should be saved.


reversion.get_ignore_duplicates()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns whether duplicate revisions will be saved.

Throws :ref:`RevisionManagementError` if there is no active revision block.


Metadata API
------------

reversion.set_user(user)
^^^^^^^^^^^^^^^^^^^^^^^^

Sets the user for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``user``
    A ``User`` model instance (or whatever your ``settings.AUTH_USER_MODEL`` is).


reversion.get_user()
^^^^^^^^^^^^^^^^^^^^

Returns the user for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.


reversion.set_comment(comment)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets the comment for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``comment``
    The text comment for the revision.


reversion.get_comment()
^^^^^^^^^^^^^^^^^^^^^^^

Returns the comment for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.


reversion.set_date_created(date_created)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets the creation date for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``date_created``
    The creation date for the revision.


reversion.get_date_created()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the creation date for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.


reversion.add_meta(model, \*\*values)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adds custom metadata to a revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

.. include:: /_include/meta-args.rst


.. _raw-revision-api:

Raw revision API
----------------

reversion.save_revision(objects, ignore_duplicates=False, user=None, comment="", meta=(), date_created=None, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Manually saves a revision without having to create a revision block and call `save()` on registered model instances.
Returns the :ref:`Revision` that was created, or ``None`` if no revision was saved.

``objects``
    An iterable of model instances to save in the revision.

``ignore_duplicates``
    .. include:: /_include/ignore-duplicates.rst

``user``
    A ``User`` model to add to the revision metadata.

``comment``
    A text comment to add to the revision metadata.

``meta``
    An iterable of unsaved model instances, representing meta information for the revision. Each instance must have a ``ForeignKey`` or ``OneToOneField`` to :ref:`Revision` named ``revision``. On revision save, the ``revision`` relation will be populated and the meta model will be saved in the same transaction.

``date_created``
    The date to associate with the revision. Defaults to ``django.utils.timezone.now()``.

``db``
    The database to save the revision into.


.. _lookup-api:

Lookup API
----------

reversion.get_for_model(model, db=None, model_db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    A registered model.

``db``
    The database to load the versions from.

``model_db``
    The database where the model is saved. Defaults to the default database for the model.



reversion.get_for_object(obj, db=None, model_db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model instance. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``obj``
    An instance of a registered model.

``db``
    The database to load the versions from.

``model_db``
    The database where the model is saved. Defaults to the default database for the model.


reversion.get_for_object_reference(model, pk, db=None, model_db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model instance. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    A registered model.

``pk``
    The database primary key of a model instance.

``db``
    The database to load the versions from.

``model_db``
    The database where the model is saved. Defaults to the default database for the model.


reversion.get_deleted(model, db=None, model_db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model containing versions where the serialized model no longer exists in the database. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    A registered model.

``db``
    The database to load the versions from.

``model_db``
    The database to check against for live model instances. Defaults to the default database for the model.


.. _VersionQuerySet:

reversion.models.VersionQuerySet
--------------------------------

A ``QuerySet`` of :ref:`Version`.


VersionQuerySet.get_unique()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of :ref:`Version`, where each version is unique for a given database, model instance, and set of serialized fields.


.. _Version:

reversion.models.Version
------------------------

Represents a single model instance serialized in a revision.


Version.pk
^^^^^^^^^^

The database primary key of the :ref:`Version`.


Version.revision
^^^^^^^^^^^^^^^^

A ``ForeignKey`` to a :ref:`Revision` instance.


Version.content_type
^^^^^^^^^^^^^^^^^^^^

The ``ContentType`` of the serialized model instance.


Version.object_id
^^^^^^^^^^^^^^^^^

The string representation of the serialized model instance's primary key.


Version.db
^^^^^^^^^^

The Django database alias where the serialized model was saved.


Version.format
^^^^^^^^^^^^^^

The name of the Django serialization format used to serialize the model instance.


Version.serialized_data
^^^^^^^^^^^^^^^^^^^^^^^

The raw serialized data of the model instance.


Version.object_repr
^^^^^^^^^^^^^^^^^^^

The stored snapshot of the model instance's ``__str__`` method when the instance was serialized.


Version.field_dict
^^^^^^^^^^^^^^^^^^

A dictionary of stored model fields. This includes fields from any parent models in the same revision.

Throws :ref:`RevertError` if the model could not be loaded, e.g. the serialized data is not compatible with the current database schema, due to database migrations.


Version.revert()
^^^^^^^^^^^^^^^^

Restores the serialized model instance to the database. To restore the entire revision, use :ref:`Revision-revert`.

Throws :ref:`RevertError` if the model could not be reverted, e.g. the serialized data is not compatible with the current database schema, due to database migrations.


.. _Revision:

reversion.models.Revision
-------------------------

Contains metadata about a revision, and groups together all :ref:`Version` instances created in that revision.


Revision.pk
^^^^^^^^^^^

The database primary key of the :ref:`Revision`.


Revision.revision_manager
^^^^^^^^^^^^^^^^^^^^^^^^^

The :ref:`RevisionManager` used to save the revision.


Revision.date_created
^^^^^^^^^^^^^^^^^^^^^

A ``datetime`` when the revision was created.


Revision.user
^^^^^^^^^^^^^

The ``User`` that created the revision, or None.


Revision.comment
^^^^^^^^^^^^^^^^

A text comment on the revision.


.. _Revision-revert:

Revision.revert(delete=False)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Restores all contained serialized model instances to the database.

Throws :ref:`RevertError` if the model could not be reverted, e.g. the serialized data is not compatible with the current database schema, due to database migrations.

``delete``
    If ``True``, any model instances which have been created and are reachable by the ``follow`` clause of any model instances in this revision will be deleted. This effectively restores a group of related models to the state they were in when the revision was created.


.. _RevisionManager:

reversion.RevisionManager
-------------------------

To support multiple configurations of django-reversion in the same project, create a standalone :ref:`RevisionManager` to act as a completely separate source of registration.

.. code:: python

    from django.db import models
    import reversion

    # Create a custom revision manager.
    my_revision_manager = RevisionManager("custom")

    # Register with the default revision manager.
    @reversion.register()
    # Register with a custom revision manager.
    @my_revision_manager.register()
    class MyModel(models.Model):

        pass

A separate :ref:`Revision` will be saved for every :ref:`RevisionManager` that a given model is registered with.

Use your custom :ref:`RevisionManager` as a namespace to access the :ref:`registration-api`, :ref:`raw-revision-api` and :ref:`lookup-api`.

.. code:: python

    versions = my_revision_manager.get_for_object(my_instance)


RevisionManager.__init__(self, manager_slug)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creates a new :ref:`RevisionManager`.

``manager_slug``
    A unique text name for the manager. If the name has already been used in your project, a :ref:`RegistrationError` will be raised.


.. _VersionAdapter:

reversion.VersionAdapter
------------------------

Customize almost every aspect of model registration by supplying a subclass of :ref:`VersionAdapter` to :ref:`register`.


VersionAdapter.fields = None
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of field names to include in the serialized data. If ``None``, all fields will be included.


VersionAdapter.exclude = ()
^^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of field names to exclude from the serialized data.


VersionAdapter.get_fields_to_serialize(self, obj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of field names to serialize in the version data.

``obj``
    The model instance being saved in the revision.


VersionAdapter.follow = ()
^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of model relationships to follow when saving a version of this model. ``ForeignKey``, ``ManyToManyField`` and reversion ``ForeignKey`` relationships are supported. Any property that returns a ``Model`` or ``QuerySet`` is also supported.


VersionAdapter.get_followed_relations(self, obj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of related model instances that should be included in the revision data.

``obj``
    The model instance being saved in the revision.


VersionAdapter.format = "json"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The name of a Django serialization format to use when saving the model instance.


VersionAdapter.get_serialization_format(self, obj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the name of a Django serialization format to use when saving the model instance.

``obj``
    The model instance being saved in the revision.


VersionAdapter.for_concrete_model = True
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If ``True`` proxy models will be saved under the same content type as their concrete model. If ``False``, proxy models will be saved under their own content type, effectively giving proxy models their own distinct history.


VersionAdapter.signals = (post_save,)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of Django signals that will trigger adding the model instance to an active revision.


VersionAdapter.get_signals(self)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of all signals that trigger saving a version.


VersionAdapter.eager_signals = ()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of Django signals that will trigger adding the model instance to an active revision. Unlike ``signals``, model instances triggering this signal will be serialized immediately, rather than at the end of the revision block. This makes it suitable for usage with signals like ``pre_delete``.


VersionAdapter.get_serialized_data(self, obj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a string of serialized data for the given model instance.

``obj``
    The model instance being saved in the revision.


VersionAdapter.get_content_type(self, db)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of (app_label, model_name) for the registered model.

``db``
    The database where the revision data will be saved.


VersionAdapter.get_object_id(self, obj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a string representation of the object's primary key.

``obj``
    The model instance being saved in the revision.


VersionAdapter.get_version_data(self, obj, model_db)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a dictionary of values to be set on the :ref:`Version` model.

``obj``
    The model instance being saved in the revision.

``model_db``
    The database where the model is saved.


VersionAdapter.revert(self, version):
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Saves the :ref:`Version` to the database.

``version``

    The :ref:`Version` to save to the database.
