"""Admin extensions for django-reversion."""

from __future__ import unicode_literals

from contextlib import contextmanager

from django.db import models, transaction
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin import helpers, options
try:
    from django.contrib.admin.utils import unquote, quote, flatten_fieldsets
except ImportError:  # Django < 1.7  pragma: no cover
    from django.contrib.admin.util import unquote, quote, flatten_fieldsets
try:
    from django.contrib.contenttypes.admin import GenericInlineModelAdmin
    from django.contrib.contenttypes.fields import GenericRelation
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericInlineModelAdmin, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.utils.formats import localize

from reversion.models import Version
from reversion.revisions import default_revision_manager


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
            yield

    # Messages.

    def log_addition(self, request, object):
        self.revision_context_manager.set_comment(_("Initial version."))
        super(VersionAdmin, self).log_addition(request, object)

    def log_change(self, request, object, message):
        self.revision_context_manager.set_comment(message)
        super(VersionAdmin, self).log_change(request, object, message)

    # Customization hooks.

    def get_revision_form_data(self, request, obj, version):
        """
        Returns a dictionary of data to set in the admin form in order to revert
        to the given revision.
        """
        return version.field_dict

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
                accessor = inline_model._meta.get_field(fk_name).related.get_accessor_name()
                follow_field = accessor
        return inline_model, follow_field, fk_name

    def __init__(self, *args, **kwargs):
        """Initializes the VersionAdmin"""
        super(VersionAdmin, self).__init__(*args, **kwargs)
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
        reversion_urls = patterns("",
                                  url("^recover/$", admin_site.admin_view(self.recoverlist_view), name='%s_%s_recoverlist' % info),
                                  url("^recover/([^/]+)/$", admin_site.admin_view(self.recover_view), name='%s_%s_recover' % info),
                                  url("^([^/]+)/history/([^/]+)/$", admin_site.admin_view(self.revision_view), name='%s_%s_revision' % info),)
        return reversion_urls + urls

    def recoverlist_view(self, request, extra_context=None):
        """Displays a deleted model to allow recovery."""
        # check if user has change or add permissions for model
        if not self.has_change_permission(request) and not self.has_add_permission(request):  # pragma: no cover
            raise PermissionDenied
        model = self.model
        opts = model._meta
        deleted = self._order_version_queryset(self.revision_manager.get_deleted(self.model))
        context = dict(
            self.admin_site.each_context(request),
            opts = opts,
            app_label = opts.app_label,
            module_name = capfirst(opts.verbose_name),
            title = _("Recover deleted %(name)s") % {"name": force_text(opts.verbose_name_plural)},
            deleted = deleted,
        )
        context.update(extra_context or {})
        return render(request, self.recover_list_template or self._get_template_list("recover_list.html"), context)

    def _hack_inline_formset_initial(self, inline, FormSet, formset, obj, version, revert, recover):
        """Hacks the given formset to contain the correct initial data."""
        # If the FK this inline formset represents is not being followed, don't process data for it.
        # see https://github.com/etianen/django-reversion/issues/222
        _, follow_field, fk_name = self._introspect_inline_admin(inline.__class__)
        if follow_field not in self.revision_manager.get_adapter(self.model).follow:
            return
        # Now we hack it to push in the data from the revision!
        initial = []
        for related_version in version.revision.version_set.all():
            if ContentType.objects.get_for_id(related_version.content_type_id).model_class() == FormSet.model and force_text(related_version.field_dict[fk_name]) == force_text(obj.pk):
                initial.append(related_version.field_dict)
        # Reconstruct the forms with the new revision data.
        formset.initial = initial
        formset.forms = [formset._construct_form(n) for n in range(len(initial))]
        def total_form_count_hack(count):
            return lambda: count
        formset.total_form_count = total_form_count_hack(len(initial))

    def render_revision_form(self, request, obj, version, extra_context, revert=False, recover=False):
        """Renders the object revision form."""
        model = self.model
        opts = model._meta
        object_id = obj.pk
        # Generate the model form.
        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == "POST":
            version.revision.revert(delete=True)
            new_object = model.objects.get(pk=object_id)
            change_message = _("Reverted to previous version, saved on %(datetime)s") % {"datetime": localize(version.revision.date_created)}
            self.log_change(request, new_object, change_message)
            self.message_user(request, _('The %(model)s "%(name)s" was reverted successfully. You may edit it again below.') % {"model": force_text(opts.verbose_name), "name": force_text(obj)})
            # Redirect to the model change form.
            return redirect("admin:{}_{}_change".format(opts.app_label, opts.model_name), new_object.pk)
        else:
            form = ModelForm(instance=obj, initial=self.get_revision_form_data(request, obj, version))
            formsets, inline_instances = self._create_formsets(request, obj, change=True)
        # Generate admin form helper.
        fieldsets = list(self.get_fieldsets(request, obj))
        adminForm = helpers.AdminForm(
            form,
            fieldsets,
            self.get_prepopulated_fields(request, obj),
            flatten_fieldsets(fieldsets),  # Set all fields to read-only.
            model_admin=self)
        media = self.media + adminForm.media
        # Generate formset helpers.
        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            prepopulated = dict(inline.get_prepopulated_fields(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
        # Generate the context.
        view_on_site_url = self.get_view_on_site_url(obj)
        context = dict(
            self.admin_site.each_context(request),
            adminform = adminForm,
            object_id = object_id,
            original = obj,
            is_popup = False,
            media = media,
            inline_admin_formsets = inline_admin_formsets,
            errors = helpers.AdminErrorList(form, formsets),
            preserved_filters = self.get_preserved_filters(request),
            add = False,
            change = True,
            revert = revert,
            recover = recover,
            has_add_permission = self.has_add_permission(request),
            has_change_permission = self.has_change_permission(request, obj),
            has_delete_permission = self.has_delete_permission(request, obj),
            has_file_field = True,
            has_absolute_url = view_on_site_url is not None,
            form_url = mark_safe(request.path),
            opts = opts,
            content_type_id = options.get_content_type_for_model(self.model).pk,
            save_as = False,
            save_on_top = self.save_on_top,
            to_field_var = options.TO_FIELD_VAR,
            is_popup_var = options.IS_POPUP_VAR,
            app_label = opts.app_label,
        )
        context.update(extra_context)
        # Render the form.
        if revert:
            form_template = self.revision_form_template or self._get_template_list("revision_form.html")
        elif recover:
            form_template = self.recover_form_template or self._get_template_list("recover_form.html")
        else:
            assert False
        return render(request, form_template, context)

    # Views.

    def add_view(self, request, form_url='', extra_context=None):
        with self._create_revision(request):
            return super(VersionAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        with self._create_revision(request):
            return super(VersionAdmin, self).change_view(request, object_id, form_url, extra_context)

    def recover_view(self, request, version_id, extra_context=None):
        """Displays a form that can recover a deleted model."""
        with self._create_revision(request):
            version = get_object_or_404(Version, pk=version_id)
            obj = version.object_version.object
            # Check if user has both change and add permissions for model.
            if not self.has_change_permission(request, obj) or not self.has_add_permission(request):  # pragma: no cover
                raise PermissionDenied
            # Create the context.
            context = {"title": _("Recover %(name)s") % {"name": version.object_repr},}
            context.update(extra_context or {})
            return self.render_revision_form(request, obj, version, context, recover=True)

    def revision_view(self, request, object_id, version_id, extra_context=None):
        """Displays the contents of the given revision."""
        with self._create_revision(request):
            object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
            obj = get_object_or_404(self.model, pk=object_id)
            version = get_object_or_404(Version, pk=version_id, object_id=force_text(obj.pk))
            # Check if user has change permissions for model.
            if not self.has_change_permission(request, obj):  # pragma: no cover
                raise PermissionDenied
            # Generate the context.
            context = {"title": _("Revert %(name)s") % {"name": force_text(self.model._meta.verbose_name)},}
            context.update(extra_context or {})
            return self.render_revision_form(request, obj, version, context, revert=True)

    def changelist_view(self, request, extra_context=None):
        """Renders the change view."""
        with self._create_revision(request):
            return super(VersionAdmin, self).changelist_view(request, extra_context)

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
