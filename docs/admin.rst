.. _admin:

Admin integration
=================

django-reversion can be used to add rollback and recovery to your admin site.


Basic usage
-----------

Registering models
^^^^^^^^^^^^^^^^^^

.. include:: _include/admin.rst

.. Note::

    If you've registered your models using the :ref:`api`, the admin class will honour the configuration you specify there. Otherwise, the admin class will auto-register your model, following all inline model relations and parent superclasses.


Integration with 3rd party apps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use ``VersionAdmin`` as a mixin with a 3rd party admin class.

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


API reference
-------------

``reversion.admin.VersionAdmin``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A subclass of ``django.contrib.ModelAdmin`` providing rollback and recovery.


``VersionAdmin.revision_form_template = None``

    A custom template to render the revision form.


``VersionAdmin.recover_list_template = None``

    A custom template to render the recover list.


``VersionAdmin.recover_form_template = None``

    A custom template to render the recover form.


``VersionAdmin.revision_manager = reversion.default_revision_manager``

    The revision manager used to manage revisions. See :ref:`low-level API <api>`.


``VersionAdmin.reversion_format = "json"``

    The serialization format to use when registering models.


``VersionAdmin.ignore_duplicate_revisions = False``

    .. include:: _include/ignore-duplicates.rst


``VersionAdmin.history_latest_first = False``

    If ``True``, revisions will be displayed with the most recent revision first.


``VersionAdmin.reversion_register(self, model, **options)``

    Callback used by the autoregistration machinery to register the model with django-reversion. Override this to customize how models are registered.

    .. code:: python

        def reversion_register(self, model, **options):
            options["exclude"] = ("some_field",)
            super(YourModelAdmin, self).reversion_register(model, **options)

    See :ref:`low-level API <api>`.


Customizing admin templates
---------------------------

Create specially named templates to override the default templates on a per-model or per-app basis.

For example, to override the ``recover_list`` template for the ``User`` model, the ``auth`` app, or all registered models, create a template with one of the following names:

*   ``'reversion/auth/user/recover_list.html'``
*   ``'reversion/auth/recover_list.html'``
*   ``'reversion/recover_list.html'``
