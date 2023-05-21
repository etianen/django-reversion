.. _admin:

Admin integration
=================

django-reversion can be used to add rollback and recovery to your admin site.

.. Important::
    Using the admin integration's preview feature will restore your model inside a temporary transaction, then roll
    back the transaction once the preview is rendered.

    The ``Model.save()`` method, along with any ``pre_save`` and ``post_save`` signals, will be run as part of the preview transaction. Any non-transactional side-effects of these functions (e.g. filesystem, cache) will **not be rolled back** at the end of the preview.

    The ``raw=True`` flag will be set in ``pre_save`` and ``post_save`` signals, allowing you to distinguish preview transactions from regular database transactions and avoid non-transactional side-effects.

    Alternatively, use `transaction.on_commit() <https://docs.djangoproject.com/en/4.2/topics/db/transactions/#django.db.transaction.on_commit>`_ to register side-effects to be carried out only on committed transactions.

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
