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
    If you're using the :ref:`admin`, model registration is automatic. If you’re using django-reversion in a management command, make sure you call ``django.contrib.admin.autodiscover()`` to load the admin modules before using the django-reversion API.

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

You can load a :ref:`VersionQuerySet` of versions from the database. Versions are loaded with the most recent version first.

.. code:: python

    from reversion.models import Version

    # Load a queryset of versions for a specific model instance.
    versions = Version.objects.get_for_object(instance)
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

``reversion.register(model, **options)``

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

    ``ignore_duplicates=False``
        If ``True``, then an additional check is performed to avoid saving duplicate versions for this model.

        Checking for duplicate revisions adds significant overhead to the process of creating a revision. Don't enable it unless you really need it!

    .. Hint::
        By default, django-reversion will not register any parent classes of a model that uses multi-table inheritance. If you wish to also add parent models to your revision, you must explicitly add their ``parent_ptr`` fields to the ``follow`` parameter when you register the model.

    .. include:: /_include/post-register.rst


``reversion.is_registered(model)``

    Returns whether the given model has been registered with django-reversion.

    ``model``
        The Django model to check.


``reversion.unregister(model)``

    Unregisters the given model from django-reversion.

    .. include:: /_include/throws-registration-error.rst

    ``model``
        The Django model to unregister.


``reversion.get_registered_models()``

    Returns an iterable of all registered models.


.. _revision-api:

Revision API
------------

``reversion.create_revision(manage_manually=False, using=None, atomic=True)``

    Marks a block of code as a *revision block*. Can also be used as a decorator.

    .. include:: /_include/create-revision-args.rst


``reversion.is_active()``

    Returns whether there is currently an active revision block.


``reversion.is_manage_manually()``

    Returns whether the current revision block is in ``manage_manually`` mode.


``reversion.set_user(user)``

    Sets the user for the current revision.

    .. include:: /_include/throws-revision-error.rst

    ``user``
        A ``User`` model instance (or whatever your ``settings.AUTH_USER_MODEL`` is).


``reversion.get_user()``

    Returns the user for the current revision.

    .. include:: /_include/throws-revision-error.rst


.. _set_comment:

``reversion.set_comment(comment)``

    Sets the comment for the current revision.

    .. include:: /_include/throws-revision-error.rst

    ``comment``
        The text comment for the revision.


``reversion.get_comment()``

    Returns the comment for the current revision.

    .. include:: /_include/throws-revision-error.rst


``reversion.set_date_created(date_created)``

    Sets the creation date for the current revision.

    .. include:: /_include/throws-revision-error.rst

    ``date_created``
        The creation date for the revision.


``reversion.get_date_created()``

    Returns the creation date for the current revision.

    .. include:: /_include/throws-revision-error.rst


``reversion.add_meta(model, **values)``

    Adds custom metadata to a revision.

    .. include:: /_include/throws-revision-error.rst

    ``model``
        A Django model to store the custom metadata. The model must have a ``ForeignKey`` or ``OneToOneField`` to :ref:`Revision`.

    ``**values``
        Values to be stored on ``model`` when it is saved.


``reversion.add_to_revision(obj, model_db=None)``

    Adds a model instance to a revision.

    .. include:: /_include/throws-revision-error.rst

    ``obj``
        A model instance to add to the revision.

    .. include:: /_include/model-db-arg.rst


.. _VersionQuerySet:

reversion.models.VersionQuerySet
--------------------------------

A ``QuerySet`` of :ref:`Version`. The results are ordered with the most recent :ref:`Version` first.


``Version.objects.get_for_model(model, model_db=None)``

    Returns a :ref:`VersionQuerySet` for the given model.

    .. include:: /_include/throws-registration-error.rst

    ``model``
        A registered model.

    .. include:: /_include/model-db-arg.rst


``Version.objects.get_for_object(obj, model_db=None)``

    Returns a :ref:`VersionQuerySet` for the given model instance.

    .. include:: /_include/throws-registration-error.rst

    ``obj``
        An instance of a registered model.

    .. include:: /_include/model-db-arg.rst


``Version.objects.get_for_object_reference(model, pk, model_db=None)``

    Returns a :ref:`VersionQuerySet` for the given model and primary key.

    .. include:: /_include/throws-registration-error.rst

    ``model``
        A registered model.

    ``pk``
        The database primary key of a model instance.

    .. include:: /_include/model-db-arg.rst


``Version.objects.get_deleted(model, model_db=None)``

    Returns a :ref:`VersionQuerySet` for the given model containing versions where the serialized model no longer exists in the database.

    .. include:: /_include/throws-registration-error.rst

    ``model``
        A registered model.

    ``db``
        The database to load the versions from.

    .. include:: /_include/model-db-arg.rst


``Version.objects.get_unique()``

    Returns an iterable of :ref:`Version`, where each version is unique for a given database, model instance, and set of serialized fields.


.. _Version:

reversion.models.Version
------------------------

Represents a single model instance serialized in a revision.


``Version.id``

    The database primary key of the :ref:`Version`.


``Version.revision``

    A ``ForeignKey`` to a :ref:`Revision` instance.


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

    .. include:: /_include/throws-revert-error.rst


``Version.revert()``

    Restores the serialized model instance to the database. To restore the entire revision, use :ref:`Revision.revert() <Revision-revert>`.

    .. include:: /_include/throws-revert-error.rst


.. _Revision:

reversion.models.Revision
-------------------------

Contains metadata about a revision, and groups together all :ref:`Version` instances created in that revision.

``Revision.id``

    The database primary key of the :ref:`Revision`.


``Revision.date_created``

    A ``datetime`` when the revision was created.


``Revision.user``

    The ``User`` that created the revision, or None.


``Revision.comment``

    A text comment on the revision.


.. _Revision-revert:

``Revision.revert(delete=False)``

    Restores all contained serialized model instances to the database.

    .. include:: /_include/throws-revert-error.rst

    ``delete``
        If ``True``, any model instances which have been created and are reachable by the ``follow`` clause of any model instances in this revision will be deleted. This effectively restores a group of related models to the state they were in when the revision was created.
