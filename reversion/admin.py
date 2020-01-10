from contextlib import contextmanager
from django.db import models, transaction, connection
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin import options
from django.contrib.admin.utils import unquote, quote
from django.contrib.contenttypes.admin import GenericInlineModelAdmin
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.text import capfirst
from django.utils.timezone import template_localtime
from django.utils.translation import ugettext as _
from django.utils.encoding import force_str
from django.utils.formats import localize
from reversion.errors import RevertError
from reversion.models import Version
from reversion.revisions import is_active, register, is_registered, set_comment, create_revision, set_user
from reversion.views import _RollBackRevisionView


class VersionAdmin(admin.ModelAdmin):

    object_history_template = "reversion/object_history.html"

    change_list_template = "reversion/change_list.html"

    revision_form_template = None

    recover_list_template = None

    recover_form_template = None

    history_latest_first = False

    def reversion_register(self, model, **kwargs):
        """Registers the model with reversion."""
        register(model, **kwargs)

    @contextmanager
    def create_revision(self, request):
        with create_revision():
            set_user(request.user)
            yield

    # Revision helpers.

    def _reversion_get_template_list(self, template_name):
        opts = self.model._meta
        return (
            "reversion/%s/%s/%s" % (opts.app_label, opts.object_name.lower(), template_name),
            "reversion/%s/%s" % (opts.app_label, template_name),
            "reversion/%s" % template_name,
        )

    def _reversion_order_version_queryset(self, queryset):
        """Applies the correct ordering to the given version queryset."""
        if not self.history_latest_first:
            queryset = queryset.order_by("pk")
        return queryset

    # Messages.

    def log_addition(self, request, object, message):
        change_message = message or _("Initial version.")
        entry = super().log_addition(request, object, change_message)
        if is_active():
            set_comment(entry.get_change_message())
        return entry

    def log_change(self, request, object, message):
        entry = super().log_change(request, object, message)
        if is_active():
            set_comment(entry.get_change_message())
        return entry

    # Auto-registration.

    def _reversion_autoregister(self, model, follow):
        if not is_registered(model):
            for parent_model, field in model._meta.concrete_model._meta.parents.items():
                follow += (field.name,)
                self._reversion_autoregister(parent_model, ())
            self.reversion_register(model, follow=follow)

    def _reversion_introspect_inline_admin(self, inline):
        inline_model = None
        follow_field = None
        fk_name = None
        if issubclass(inline, GenericInlineModelAdmin):
            inline_model = inline.model
            ct_field = inline.ct_field
            fk_name = inline.ct_fk_field
            for field in self.model._meta.private_fields:
                if (
                    isinstance(field, GenericRelation) and
                    field.remote_field.model == inline_model and
                    field.object_id_field_name == fk_name and
                    field.content_type_field_name == ct_field
                ):
                    follow_field = field.name
                    break
        elif issubclass(inline, options.InlineModelAdmin):
            inline_model = inline.model
            fk_name = inline.fk_name
            if not fk_name:
                for field in inline_model._meta.get_fields():
                    if (
                        isinstance(field, (models.ForeignKey, models.OneToOneField)) and
                        issubclass(self.model, field.remote_field.model)
                    ):
                        fk_name = field.name
                        break
            if fk_name and not inline_model._meta.get_field(fk_name).remote_field.is_hidden():
                field = inline_model._meta.get_field(fk_name)
                accessor = field.remote_field.get_accessor_name()
                follow_field = accessor
        return inline_model, follow_field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatically register models if required.
        if not is_registered(self.model):
            inline_fields = ()
            for inline in self.inlines:
                inline_model, follow_field = self._reversion_introspect_inline_admin(inline)
                if inline_model:
                    self._reversion_autoregister(inline_model, ())
                if follow_field:
                    inline_fields += (follow_field,)
            self._reversion_autoregister(self.model, inline_fields)

    def get_urls(self):
        urls = super().get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        reversion_urls = [
            url(r"^recover/$", admin_site.admin_view(self.recoverlist_view), name='%s_%s_recoverlist' % info),
            url(r"^recover/(\d+)/$", admin_site.admin_view(self.recover_view), name='%s_%s_recover' % info),
            url(r"^([^/]+)/history/(\d+)/$", admin_site.admin_view(self.revision_view), name='%s_%s_revision' % info),
        ]
        return reversion_urls + urls

    # Views.

    def add_view(self, request, form_url='', extra_context=None):
        with self.create_revision(request):
            return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        with self.create_revision(request):
            return super().change_view(request, object_id, form_url, extra_context)

    def _reversion_revisionform_view(self, request, version, template_name, extra_context=None):
        # Check that database transactions are supported.
        if not connection.features.uses_savepoints:
            raise ImproperlyConfigured("Cannot use VersionAdmin with a database that does not support savepoints.")
        # Run the view.
        try:
            with transaction.atomic(using=version.db):
                # Revert the revision.
                version.revision.revert(delete=True)
                # Run the normal changeform view.
                with self.create_revision(request):
                    response = self.changeform_view(request, quote(version.object_id), request.path, extra_context)
                    # Decide on whether the keep the changes.
                    if request.method == "POST" and response.status_code == 302:
                        set_comment(_("Reverted to previous version, saved on %(datetime)s") % {
                            "datetime": localize(template_localtime(version.revision.date_created)),
                        })
                    else:
                        response.template_name = template_name  # Set the template name to the correct template.
                        response.render()  # Eagerly render the response, so it's using the latest version.
                        raise _RollBackRevisionView(response)  # Raise exception to undo the transaction and revision.
        except (RevertError, models.ProtectedError) as ex:
            opts = self.model._meta
            messages.error(request, force_str(ex))
            return redirect("{}:{}_{}_changelist".format(self.admin_site.name, opts.app_label, opts.model_name))
        except _RollBackRevisionView as ex:
            return ex.response
        return response

    def recover_view(self, request, version_id, extra_context=None):
        """Displays a form that can recover a deleted model."""
        # The revisionform view will check for change permission (via changeform_view),
        # but we also need to check for add permissions here.
        if not self.has_add_permission(request):
            raise PermissionDenied
        # Render the recover view.
        version = get_object_or_404(Version, pk=version_id)
        context = {
            "title": _("Recover %(name)s") % {"name": version.object_repr},
            "recover": True,
        }
        context.update(extra_context or {})
        return self._reversion_revisionform_view(
            request,
            version,
            self.recover_form_template or self._reversion_get_template_list("recover_form.html"),
            context,
        )

    def revision_view(self, request, object_id, version_id, extra_context=None):
        """Displays the contents of the given revision."""
        object_id = unquote(object_id)  # Underscores in primary key get quoted to "_5F"
        version = get_object_or_404(Version, pk=version_id, object_id=object_id)
        context = {
            "title": _("Revert %(name)s") % {"name": version.object_repr},
            "revert": True,
        }
        context.update(extra_context or {})
        return self._reversion_revisionform_view(
            request,
            version,
            self.revision_form_template or self._reversion_get_template_list("revision_form.html"),
            context,
        )

    def changelist_view(self, request, extra_context=None):
        with self.create_revision(request):
            context = {
                "has_change_permission": self.has_change_permission(request),
            }
            context.update(extra_context or {})
            return super().changelist_view(request, context)

    def recoverlist_view(self, request, extra_context=None):
        """Displays a deleted model to allow recovery."""
        # Check if user has change and add permissions for model
        if not self.has_change_permission(request) or not self.has_add_permission(request):
            raise PermissionDenied
        model = self.model
        opts = model._meta
        deleted = self._reversion_order_version_queryset(Version.objects.get_deleted(self.model))
        # Set the app name.
        request.current_app = self.admin_site.name
        # Get the rest of the context.
        context = dict(
            self.admin_site.each_context(request),
            opts=opts,
            app_label=opts.app_label,
            module_name=capfirst(opts.verbose_name),
            title=_("Recover deleted %(name)s") % {"name": force_str(opts.verbose_name_plural)},
            deleted=deleted,
        )
        context.update(extra_context or {})
        return render(
            request,
            self.recover_list_template or self._reversion_get_template_list("recover_list.html"),
            context,
        )

    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        # Check if user has view or change permissions for model
        if hasattr(self, 'has_view_or_change_permission'):  # for Django >= 2.1
            if not self.has_view_or_change_permission(request):
                raise PermissionDenied
        else:
            if not self.has_change_permission(request):
                raise PermissionDenied

        opts = self.model._meta
        action_list = [
            {
                "revision": version.revision,
                "url": reverse(
                    "%s:%s_%s_revision" % (self.admin_site.name, opts.app_label, opts.model_name),
                    args=(quote(version.object_id), version.id)
                ),
            }
            for version
            in self._reversion_order_version_queryset(Version.objects.get_for_object_reference(
                self.model,
                unquote(object_id),  # Underscores in primary key get quoted to "_5F"
            ).select_related("revision__user"))
        ]
        # Compile the context.
        context = {"action_list": action_list}
        context.update(extra_context or {})
        return super().history_view(request, object_id, context)
