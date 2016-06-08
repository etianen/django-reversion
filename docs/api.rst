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
    from reversion import revisions

    @revisions.register()
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
    with revisions.create_revision():

        # Save a new model instance.
        obj = YourModel()
        obj.name = "obj v1"
        obj.save()

        # Store some meta-information.
        revisions.set_user(request.user)
        revisions.set_comment("Created revision 1")

    # Declare a new revision block.
    with revisions.create_revision():

        # Update the model instance.
        obj.name = "obj v2"
        obj.save()

        # Store some meta-information.
        revisions.set_user(request.user)
        revisions.set_comment("Created revision 2")

.. Important::

    Bulk actions, such as ``Queryset.update()``, do not send signals, so won't be noticed by django-reversion.


Loading revisions
^^^^^^^^^^^^^^^^^

Each model instance saved in a revision block is serialized as a :ref:`Version`. All versions in a revision block are associated with a single :ref:`Revision`.

You can load a ``Queryset`` of versions from the database. Versions are loaded with the most recent version first.

.. code:: python

    # Load a queryset of versions for a specific model instance.
    versions = revisions.get_for_object(instance)
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

reversion.revisions.register(model, \*\*options)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    A tuple of Django signals that will trigger adding the model instance to an active revision.

``eager_signals=()``
    A tuple of Django signals that will trigger adding the model instance to an active revision. Unlike ``signals``, model instances triggering this signal will be serialized immediately, rather than at the end of the revision block. This makes it suitable for usage with signals like ``pre_delete``.

``adapter_cls=reversion.revisions.VersionAdapter``
    A subclass of :ref:`VersionAdapter` to use to register the model.

.. Hint::
    By default, django-reversion will not register any parent classes of a model that uses multi-table inheritance. If you wish to also add parent models to your revision, you must explicitly add their ``parent_ptr`` fields to the ``follow`` parameter when you register the model.

.. include:: /_include/post-register.rst


reversion.revisions.is_registered(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns whether the given model has been registered with django-reversion.

``model``
    The Django model to check.


reversion.revisions.unregister(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Unregisters the given model from django-reversion.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    The Django model to unregister.


reversion.revisions.get_registered_models()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns an iterable of all registered models.


reversion.revisions.get_adapter(model)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the :ref:`VersionAdapter` for the given model.

``model``
    The Django model look up.


.. _revision-api:

Revision API
------------

reversion.revisions.create_revision(manage_manually=False, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Marks a block of code as a *revision block*. Can also be used as a decorator. The revision block will be wrapped in a ``transaction.atomic()``.

``manage_manually``
    If ``True``, versions will not be saved when a model's ``save()`` method is called. This allows version control to be switched off for a given revision block.

``db``:
    The database to save the revision data. The revision block will be wrapped in a transaction using this database. If ``None``, the default database for :ref:`Revision` will be used.


reversion.revisions.set_ignore_duplicates(ignore_duplicates)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: /_include/ignore-duplicates.rst

Throws :ref:`RevisionManagementError` if there is no active revision block.

``ignore_duplicates``
    A ``bool`` indicating whether duplicate revisions should be saved.


reversion.revisions.get_ignore_duplicates()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns whether duplicate revisions will be saved.

Throws :ref:`RevisionManagementError` if there is no active revision block.


Metadata API
------------

reversion.revisions.set_user(user)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets the user for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``user``
    A ``User`` model instance (or whatever your ``settings.AUTH_USER_MODEL`` is).


reversion.revisions.get_user()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the user for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.


reversion.revisions.set_comment(comment)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets the comment for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``comment``
    The text comment for the revision.


reversion.revisions.get_comment()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns the comment for the current revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.


reversion.revisions.add_meta(model_cls, \*\*values)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adds custom metadata to a revision.

Throws :ref:`RevisionManagementError` if there is no active revision block.

``model_cls``
    A Django model to store the custom metadata. The model must have a ``ForeignKey`` or ``OneToOneField`` to :ref:`Revision`.

``**values``
    Values to be stored on ``model_cls`` when it is saved.


.. _raw-revision-api:

Raw revision API
----------------

reversion.revisions.save_revision(objects=(), ignore_duplicates=False, user=None, comment="", meta=(), date_created=None, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    An iterable of unsaved model instances representing additional meta information about the revision. Each model must have a ``ForeignKey`` or ``OneToOneField`` to ``reversion.models.Revision``. When the revision is saved, all meta model instances will be saved in the same transaction.

``date_created``
    The date to associate with the revision. Defaults to ``django.utils.timezone.now()``.

``db``
    The database to save the revision into.


.. _lookup-api:

Lookup API
----------

reversion.revisions.get_for_object(obj, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model instance. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``obj``
    An instance of a registered model.

``db``
    The database to load the versions from.


reversion.revisions.get_for_object_reference(model, pk, db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model instance. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    A registered model.

``pk``
    The database primary key of a model instance.

``db``
    The database to load the versions from.


reversion.revisions.get_deleted(model, db=None, model_db=None)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Returns a :ref:`VersionQuerySet` for the given model containing versions where the serialized model no longer exists in the database. The results are ordered with the most recent :ref:`Version` first.

Throws :ref:`RegistrationError` if the model has not been registered with django-reversion.

``model``
    A registered model.

``db``
    The database to load the versions from.

``model_db``
    The database to check against for live model instances. Defaults to `db`.


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
    from reversion import revisions

    # Create a custom revision manager.
    my_revision_manager = RevisionManager("custom")

    # Register with the default revision manager.
    @revisions.register()
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


VersionAdapter.follow = ()
^^^^^^^^^^^^^^^^^^^^^^^^^^

An iterable of model relationships to follow when saving a version of this model. ``ForeignKey``, ``ManyToManyField`` and reversion ``ForeignKey`` relationships are supported. Any property that returns a ``Model`` or ``QuerySet`` is also supported.


VersionAdapter.format = "json"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The name of a Django serialization format to use when saving the model instance.


VersionAdapter.for_concrete_model = True
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If ``True`` proxy models will be saved under the same content type as their concrete model. If ``False``, proxy models will be saved under their own content type, effectively giving proxy models their own distinct history.


VersionAdapter.signals = (post_save,)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A tuple of Django signals that will trigger adding the model instance to an active revision.


VersionAdapter.eager_signals = ()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A tuple of Django signals that will trigger adding the model instance to an active revision. Unlike ``signals``, model instances triggering this signal will be serialized immediately, rather than at the end of the revision block. This makes it suitable for usage with signals like ``pre_delete``.


VersionAdapter.revert(self, version):
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Saves the :ref:`Version` to the database.

``version``

    The :ref:`Version` to save to the database.
