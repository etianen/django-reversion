.. _admin:

Admin integration
=================

django-reversion can be used to add rollback and recovery to your admin site. To enable this, register your models with a subclass of ``reversion.VersionAdmin``.

::

    from reversion.admin import VersionAdmin

    class YourModelAdmin(VersionAdmin):

        pass

    admin.site.register(YourModel, YourModelAdmin)

**Important:** Whenever you register a model with django-reversion, run ``./manage.py createinitialrevisions`` command to populate the version database with an initial set of data. For large databases, this command can take a while to execute.

**Note:** If you've registered your models using the :ref:`low level API <api>`, the admin class will honour the configuration you specify there. Otherwise, the admin class will auto-register your model, following all inline model relations
and parent superclasses.

You can also use ``VersionAdmin`` as a mixin with another specialized admin class.

::

    class YourModelAdmin(VersionAdmin, YourBaseModelAdmin):

        pass

If you're using an existing third party app, you can add patch django-reversion into its admin class by using the ``reversion.helpers.patch_admin()`` method. For example, to add version control to the built-in User model:

::

    from reversion.helpers import patch_admin

    patch_admin(User)


Admin customizations
--------------------

Customize the way django-reversion integrates with your admin site by overriding options and methods on a subclass of ``VersionAdmin``:

::

    class YourModelAdmin(VersionAdmin):

        revision_form_template = None
        """The template to render the revision form."""

        recover_list_template = None
        """The template to render the recover list."""

        recover_form_template = None
        """The template to render the recover form."""

        revision_manager = default_revision_manager
        """The revision manager used to manage revisions."""

        reversion_format = "json"
        """The serialization format to use when registering models."""

        ignore_duplicate_revisions = False
        """Whether to ignore duplicate revision data."""

        history_latest_first = False
        """Display versions with the most recent version first."""

        def reversion_register(self, model, **kwargs):
            """Registers the model with reversion."""
            # Customize registration kwargs here.
            super(YourModelAdmin, self).reversion_register(model, **kwargs)


Customizing admin templates
---------------------------

Create specially named templates to override the default templates on a per-model or per-app basis.

For example, to override the ``recover_list`` template for the ``User`` model, the ``auth`` app, or all registered models, create a template with one of the following names:

*   ``'reversion/auth/user/recover_list.html'``
*   ``'reversion/auth/recover_list.html'``
*   ``'reversion/recover_list.html'``
