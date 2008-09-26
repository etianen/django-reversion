"""Admin extensions for Reversion."""


from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.html import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from reversion import revision
from reversion.models import Version


class VersionAdmin(admin.ModelAdmin):
    
    """Abstract admin class for handling version controlled models."""

    revision_form_template = "reversion/revision_form.html"
    object_history_template = "reversion/object_history.html"
    
    def __call__(self, request, url):
        """Adds additional functionality to the admin class."""
        path = url or ""
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[1] == "history":
            object_id = parts[0]
            revision_id = parts[2]
            return self.revision_view(request, object_id, revision_id)
        else:
            return super(VersionAdmin, self).__call__(request, url)
    
    @revision.create_revision
    def revision_view(self, request, object_id, revision_id):
        """Displays the contents of the given revision."""
        model = self.model
        opts = model._meta
        opts = self.model._meta
        obj = get_object_or_404(self.model, pk=object_id)
        revision = get_object_or_404(Revision, pk=revision_id)
        version = get_object_or_404(Version, object_id=object_id, revision=revision)
        object_version = version.object_version
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        # Generate the form.
        ModelForm = self.get_form(request, obj)
        formsets = []
        form = ModelForm(instance=object_version.object)
        formsets = []
        # Generate the context.
        adminForm = admin.helpers.AdminForm(form, self.get_fieldsets(request, obj), self.prepopulated_fields)
        media = self.media + adminForm.media
        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            inline_admin_formset = admin.helpers.InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
        context = {
            "title": _("Revert %s") % force_unicode(opts.verbose_name),
            "adminform": adminForm,
            "object_id": object_id,
            "original": obj,
            "is_popup": False,
            "media": mark_safe(media),
            "inline_admin_formsets": inline_admin_formsets,
            "errors": admin.helpers.AdminErrorList(form, formsets),
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "add": False,
            "change": True,
            "has_add_permission": self.has_add_permission(request),
            "has_change_permission": self.has_change_permission(request, obj),
            "has_delete_permission": self.has_delete_permission(request, obj),
            "has_file_field": True, # FIXME - this should check if form or formsets have a FileField,
            "has_absolute_url": hasattr(self.model, "get_absolute_url"),
            "ordered_objects": ordered_objects,
            "form_url": mark_safe("FOOBAR"),
            "opts": opts,
            "content_type_id": ContentType.objects.get_for_model(self.model).id,
            "save_as": self.save_as,
            "save_on_top": self.save_on_top,
            "root_path": self.admin_site.root_path,
        }
        return render_to_response(self.revision_form_template, context, context_instance=RequestContext(request))
    
    def log_addition(self, request, object):
        """Add the user to the current revision."""
        super(VersionAdmin, self).log_addition(request, object)
        current_revision = revision.get_current_revision()
        current_revision.user = request.user
        current_revision.save()
    
    def log_change(self, request, object, message):
        """Add the change message to the current revision."""
        super(VersionAdmin, self).log_change(request, object, message)
        current_revision = revision.get_current_revision()
        current_revision.comment = message
        current_revision.user = request.user
        current_revision.save()
        
    def log_deletion(self, request, object, object_repr):
        """Add the user to the current revision."""
        super(VersionAdmin, self).log_deletion(request, object, object_repr)
        current_revision = revision.get_current_revision()
        current_revision.user = request.user
        current_revision.save()
        
    # Wrap the data-modifying views in revisions.
    add_view = revision.create_revision(admin.ModelAdmin.add_view)
    change_view = revision.create_revision(admin.ModelAdmin.change_view)
    delete_view = revision.create_revision(admin.ModelAdmin.delete_view)
    
    def history_view(self, request, object_id, extra_context=None):
        """Renders an alternate history view"""
        obj = get_object_or_404(self.model, pk=object_id)
        action_list = Revision.objects.get_for_object(obj)
        context = {"action_list": action_list,}
        if extra_context:
            context.update(extra_context)
        return super(VersionAdmin, self).history_view(request, object_id, context)