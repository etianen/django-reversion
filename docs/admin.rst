.. _admin:

Admin integration
=================

django-reversion can be used to add rollback and recovery to your admin site.

.. Warning::
    The admin integration requires that your database engine supports transactions. This is the case for PostgreSQL, SQLite and MySQL InnoDB. If you are using MySQL MyISAM, upgrade your database tables to InnoDB!


Overview
--------

Registering models
^^^^^^^^^^^^^^^^^^

.. include:: /_include/admin.rst

.. Note::

    If you've registered your models using :ref:`reversion.register() <register>`, the admin class will use the configuration you specify there. Otherwise, the admin class will auto-register your model, following all inline model relations and parent superclasses. Customize the admin registration by overriding :ref:`VersionAdmin.register() <VersionAdmin_register>`.


Integration with 3rd party apps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use :ref:`VersionAdmin` as a mixin with a 3rd party admin class.

.. code:: python

    @admin.register(SomeModel)
    class YourModelAdmin(VersionAdmin, SomeModelAdmin):

        pass

If the 3rd party model is already registered with the Django admin, you may have to unregister it first.

.. code:: python

    admin.site.unregister(SomeModel)

    @admin.register(SomeModel)
    class YourModelAdmin(VersionAdmin, SomeModelAdmin):

        pass


.. _VersionAdmin:

reversion.admin.VersionAdmin
----------------------------

A subclass of ``django.contrib.ModelAdmin`` providing rollback and recovery.


``revision_form_template = None``

    A custom template to render the revision form.

    Alternatively, create specially named templates to override the default templates on a per-model or per-app basis.

    *   ``'reversion/app_label/model_name/revision_form.html'``
    *   ``'reversion/app_label/revision_form.html'``
    *   ``'reversion/revision_form.html'``


``recover_list_template = None``

    A custom template to render the recover list.

    Alternatively, create specially named templates to override the default templates on a per-model or per-app basis.

    *   ``'reversion/app_label/model_name/recover_list.html'``
    *   ``'reversion/app_label/recover_list.html'``
    *   ``'reversion/recover_list.html'``


``recover_form_template = None``

    A custom template to render the recover form.

    *   ``'reversion/app_label/model_name/recover_form.html'``
    *   ``'reversion/app_label/recover_form.html'``
    *   ``'reversion/recover_form.html'``


``history_latest_first = False``

    If ``True``, revisions will be displayed with the most recent revision first.


``history_order_by_date = False``

    If ``True``, revisions will be ordered by ``date_created`` instead of the numeric version ID.


.. _VersionAdmin_register:

``reversion_register(model, **options)``

    Callback used by the auto-registration machinery to register the model with django-reversion. Override this to customize how models are registered.

    .. code:: python

        def reversion_register(self, model, **options):
            options["exclude"] = ("some_field",)
            super().reversion_register(model, **options)

    ``model``
        The model that will be registered with django-reversion.

    ``options``
        Registration options, see :ref:`reversion.register() <register>`.

.. _VersionAdmin_get_version_ordering:

``get_version_ordering(request)``

    Method that returns a tuple specifying the field names (relative to the ``Version`` model) for ordering. Semantics are similar to the built-in ``get_ordering`` method in Django's ``ModelAdmin``.

    Implementations may override this method to achieve custom or dynamic ordering of the version queryset. The return value must be a list or tuple. Calling ``super()`` returns the default ordering which takes ``history_latest_first`` and ``history_order_by_date`` into account; this call may be omitted if the default ordering is not required.

    .. code:: python

        def get_version_ordering(self, request):
            if request.user.is_superuser:
                return ("-revision__date_created", "revision__comment")
            return super().get_version_ordering(request)

    ``request``
        The current request.
