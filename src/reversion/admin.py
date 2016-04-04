"""Admin extensions for django-reversion."""

from __future__ import unicode_literals

from contextlib import contextmanager

from django.db import models, transaction, connection
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import options
from django.contrib.admin.utils import unquote, quote
try:
    from django.contrib.contenttypes.admin import GenericInlineModelAdmin
    from django.contrib.contenttypes.fields import GenericRelation
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericInlineModelAdmin, GenericRelation
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import get_object_or_404, render
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.utils.formats import localize

from reversion.models import Version
from reversion.revisions import default_revision_manager


class RollBackRevisionView(Exception):

    pass


class VersionAdmin(admin.ModelAdmin):

    """Abstract admin class for handling version controlled models."""

    object_history_template = "reversion/object_history.html"

    change_list_template = "reversion/change_list.html"

    revision_form_template = None

    recover_list_template = None

    recover_form_template = None

    # The revision manager instance used to manage revisions.
    revision_manager = default_revision_manager

    # The serialization format to use when registering models with reversion.
    reversion_format = "json"

    # Whether to ignore duplicate revision data.
    ignore_duplicate_revisions = False

    # If True, then the default ordering of object_history and recover lists will be reversed.
    history_latest_first = False

    # Revision helpers.

    @property
    def revision_context_manager(self):
        """The revision context manager for this VersionAdmin."""
        return self.revision_manager._revision_context_manager

    def _get_template_list(self, template_name):
        opts = self.model._meta
        return (
            "reversion/%s/%s/%s" % (opts.app_label, opts.object_name.lower(), template_name),
            "reversion/%s/%s" % (opts.app_label, template_name),
            "reversion/%s" % template_name,
        )

    def _order_version_queryset(self, queryset):
        """Applies the correct ordering to the given version queryset."""
        if self.history_latest_first:
            return queryset.order_by("-pk")
        return queryset.order_by("pk")

    @contextmanager
    def _create_revision(self, request):
        with transaction.atomic(), self.revision_context_manager.create_revision():
            self.revision_context_manager.set_user(request.user)
            self.revision_context_manager.set_ignore_duplicates(self.ignore_duplicate_revisions)
            yield

    # Messages.

    def log_addition(self, request, object, change_message=None):
        change_message = change_message or _("Initial version.")
        if self.revision_context_manager.is_active():
            self.revision_context_manager.set_comment(change_message)
        try:
            super(VersionAdmin, self).log_addition(request, object, change_message)
        except TypeError:  # Django < 1.9 pragma: no cover
            super(VersionAdmin, self).log_addition(request, object)

    def log_change(self, request, object, message):
        if self.revision_context_manager.is_active():
            self.revision_context_manager.set_comment(message)
        super(VersionAdmin, self).log_change(request, object, message)

    # Auto-registration.

    def _autoregister(self, model, follow=None):
        """Registers a model with reversion, if required."""
        if not self.revision_manager.is_registered(model):
            follow = follow or []
            # Use model_meta.concrete_model to catch proxy models
            for parent_cls, field in model._meta.concrete_model._meta.parents.items():
                follow.append(field.name)
                self._autoregister(parent_cls)
            self.revision_manager.register(model, follow=follow, format=self.reversion_format)

    def _introspect_inline_admin(self, inline):
        """Introspects the given inline admin, returning a tuple of (inline_model, follow_field)."""
        inline_model = None
        follow_field = None
        fk_name = None
        if issubclass(inline, GenericInlineModelAdmin):
            inline_model = inline.model
            ct_field = inline.ct_field
            fk_name = inline.ct_fk_field
            for field in self.model._meta.virtual_fields:
                if isinstance(field, GenericRelation) and field.rel.to == inline_model and field.object_id_field_name == fk_name and field.content_type_field_name == ct_field:
                    follow_field = field.name
                    break
        elif issubclass(inline, options.InlineModelAdmin):
            inline_model = inline.model
            fk_name = inline.fk_name
            if not fk_name:
                for field in inline_model._meta.fields:
                    if isinstance(field, (models.ForeignKey, models.OneToOneField)) and issubclass(self.model, field.rel.to):
                        fk_name = field.name
                        break
            if fk_name and not inline_model._meta.get_field(fk_name).rel.is_hidden():
                field = inline_model._meta.get_field(fk_name)
                try:
                    # >=django1.9
                    remote_field = field.remote_field
                except AttributeError:
                    remote_field = field.related
                accessor = remote_field.get_accessor_name()
                follow_field = accessor
        return inline_model, follow_field, fk_name

    def __init__(self, *args, **kwargs):
        """Initializes the VersionAdmin"""
        super(VersionAdmin, self).__init__(*args, **kwargs)
        # Check that database transactions are supported.
        if not connection.features.uses_savepoints:  # pragma: no cover
            raise ImproperlyConfigured("Cannot use VersionAdmin with a database that does not support savepoints.")
        # Automatically register models if required.
        if not self.revision_manager.is_registered(self.model):
            inline_fields = []
            for inline in self.inlines:
                inline_model, follow_field, _ = self._introspect_inline_admin(inline)
                if inline_model:
                    self._autoregister(inline_model)
                if follow_field:
                    inline_fields.append(follow_field)
            self._autoregister(self.model, inline_fields)

    def get_urls(self):
        """Returns the additional urls used by the Reversion admin."""
        urls = super(VersionAdmin, self).get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        reversion_urls = [
                                  url("^recover/$", admin_site.admin_view(self.recoverlist_view), name='%s_%s_recoverlist' % info),
                                  url("^recover/([^/]+)/$", admin_site.admin_view(self.recover_view), name='%s_%s_recover' % info),
                                  url("^([^/]+)/history/([^/]+)/$", admin_site.admin_view(self.revision_view), name='%s_%s_revision' % info),]
        return reversion_urls + urls

    # Views.

    def add_view(self, request, form_url='', extra_context=None):
        with self._create_revision(request):
            return super(VersionAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        with self._create_revision(request):
            return super(VersionAdmin, self).change_view(request, object_id, form_url, extra_context)

    def revisionform_view(self, request, version, template_name, extra_context=None):
        try:
            with transaction.atomic():
                # Revert the revision.
                version.revision.revert(delete=True)
                # Run the normal changeform view.
                with self._create_revision(request):
                    response = self.changeform_view(request, version.object_id, request.path, extra_context)
                    # Decide on whether the keep the changes.
                    if request.method == "POST" and response.status_code == 302:
                        self.revision_context_manager.set_comment(_("Reverted to previous version, saved on %(datetime)s") % {"datetime": localize(version.revision.date_created)})
                    else:
                        response.template_name = template_name  # Set the template name to the correct template.
                        response.render()  # Eagerly render the response, so it's using the latest version of the database.
                        raise RollBackRevisionView  # Raise an exception to undo the transaction and the revision.
        except RollBackRevisionView:
            pass
        return response

    def recover_view(self, request, version_id, extra_context=None):
        """Displays a form that can recover a deleted model."""
        # The revisionform view will check for change permission (via changeform_view),
        # but we also need to check for add permissions here.
        if not self.has_add_permission(request):  # pragma: no cover
            raise PermissionDenied
        # Render the recover view.
        version = get_object_or_404(Version, pk=version_id)
        context = {
            "title": _("Recover %(name)s") % {"name": version.object_repr},
        }
        context.update(extra_context or {})
        return self.revisionform_view(request, version, self.recover_form_template or self._get_template_list("recover_form.html"), context)

    def revision_view(self, request, object_id, version_id, extra_context=None):
        """Displays the contents of the given revision."""
        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        version = get_object_or_404(Version, pk=version_id, object_id=object_id)
        context = {
            "title": _("Revert %(name)s") % {"name": version.object_repr},
        }
        context.update(extra_context or {})
        return self.revisionform_view(request, version, self.revision_form_template or self._get_template_list("revision_form.html"), context)

    def changelist_view(self, request, extra_context=None):
        """Renders the change view."""
        with self._create_revision(request):
            context = {
                "has_change_permission": self.has_change_permission(request),
            }
            context.update(extra_context or {})
            return super(VersionAdmin, self).changelist_view(request, context)

    def recoverlist_view(self, request, extra_context=None):
        """Displays a deleted model to allow recovery."""
        # Check if user has change or add permissions for model
        if not self.has_change_permission(request) or not self.has_add_permission(request):  # pragma: no cover
            raise PermissionDenied
        model = self.model
        opts = model._meta
        deleted = self._order_version_queryset(self.revision_manager.get_deleted(self.model))
        # Get the site context.
        try:
            each_context = self.admin_site.each_context(request)
        except TypeError:  # Django <= 1.7 pragma: no cover
            each_context = self.admin_site.each_context()
        # Get the rest of the context.
        context = dict(
            each_context,
            opts = opts,
            app_label = opts.app_label,
            module_name = capfirst(opts.verbose_name),
            title = _("Recover deleted %(name)s") % {"name": force_text(opts.verbose_name_plural)},
            deleted = deleted,
        )
        context.update(extra_context or {})
        return render(request, self.recover_list_template or self._get_template_list("recover_list.html"), context)

    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        # Check if user has change permissions for model
        if not self.has_change_permission(request):  # pragma: no cover
            raise PermissionDenied
        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        opts = self.model._meta
        action_list = [
            {
                "revision": version.revision,
                "url": reverse("%s:%s_%s_revision" % (self.admin_site.name, opts.app_label, opts.model_name), args=(quote(version.object_id), version.id)),
            }
            for version
            in self._order_version_queryset(self.revision_manager.get_for_object_reference(
                self.model,
                object_id,
            ).select_related("revision__user"))
        ]
        # Compile the context.
        context = {"action_list": action_list}
        context.update(extra_context or {})
        return super(VersionAdmin, self).history_view(request, object_id, context)
