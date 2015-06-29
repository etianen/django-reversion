.. _admin:

Admin integration
=================

django-reversion can be used to add a powerful rollback and recovery facility to your admin site. To enable this, simply register your models with a subclass of ``reversion.VersionAdmin``.

::

    import reversion

    class YourModelAdmin(reversion.VersionAdmin):

        pass

    admin.site.register(YourModel, YourModelAdmin)

You can also use ``reversion.VersionAdmin`` as a mixin with another specialized admin class.

::

    class YourModelAdmin(reversion.VersionAdmin, YourBaseModelAdmin):

        pass

If you're using an existing third party app, then you can add patch django-reversion into its admin class by using the ``reversion.helpers.patch_admin()`` method. For example, to add version control to the built-in User model:

::

    from reversion.helpers import patch_admin

    patch_admin(User)


Admin customizations
--------------------

It's possible to customize the way django-reversion integrates with your admin site by specifying options on the subclass of ``reversion.VersionAdmin`` as follows:

::

    class YourModelAdmin(reversion.VersionAdmin):

        option_name = option_value

The available admin options are:

*   **history_latest_first:** Whether to display the available versions in reverse chronological order on the revert and recover views (default ``False``)
*   **ignore_duplicate_revisions:** Whether to ignore duplicate revisions when storing version data (default ``False``)
*   **recover_form_template:** The name of the template to use when rendering the recover form (default ``'reversion/recover_form.html'``)
*   **reversion_format:** The name of a serialization format to use when storing version data (default ``'json'``)
*   **revision_form_template:** The name of the template to use when rendering the revert form (default ``'reversion/revision_form.html'``)
*   **recover_list_template:** The name of the template to use when rendering the recover list view (default ``'reversion/recover_list.html'``)


Customizing admin templates
---------------------------

In addition to specifying custom templates using the options above, you can also place specially named templates on your template root to override the default templates on a per-model or per-app basis.

For example, to override the recover_list template for the user model, the auth app, or all registered models, you could create a template with one of the following names:

*   ``'reversion/auth/user/recover_list.html'``
*   ``'reversion/auth/recover_list.html'``
*   ``'reversion/recover_list.html'``
