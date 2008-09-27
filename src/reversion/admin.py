"""Admin extensions for Reversion."""


from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.forms.formsets import all_valid
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.dateformat import format
from django.utils.encoding import force_unicode
from django.utils.html import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from reversion import revision
from reversion.models import Version


def deserialized_model_to_dict(deserialized_model, revision_data):
    """Converts a deserialized model to a dictionary."""
    result = model_to_dict(deserialized_model.object)
    result.update(deserialized_model.m2m_data)
    # Add parent data.
    model = deserialized_model.object
    for parent_class, field in model._meta.parents.items():
        attname = field.attname
        attvalue = getattr(model, attname)
        pk_name = parent_class._meta.pk.name
        for deserialized_model in revision_data:
            parent = deserialized_model.object
            if parent_class == parent.__class__ and unicode(getattr(parent, pk_name)) == unicode(getattr(model, attname)):
                result.update(deserialized_model_to_dict(deserialized_model, revision_data))
    return result


class VersionAdmin(admin.ModelAdmin):
    
    """Abstract admin class for handling version controlled models."""

    revision_form_template = "reversion/revision_form.html"
    object_history_template = "reversion/object_history.html"
    change_list_template = "reversion/change_list.html"
    recover_list_template = "reversion/recover_list.html"
    recover_form_template = "reversion/recover_form.html"
    
    def __call__(self, request, url):
        """Adds additional functionality to the admin class."""
        path = url or ""
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[1] == "history":
            object_id = parts[0]
            revision_id = parts[2]
            return self.revision_view(request, object_id, revision_id)
        elif len(parts) == 1 and parts[0] == "recover":
            return self.recover_list_view(request)
        elif len(parts) == 2 and parts[0] == "recover":
            return self.recover_view(request, parts[1])
        else:
            return super(VersionAdmin, self).__call__(request, url)
    
    def recover_list_view(self, request, extra_context=None):
        """Displays a deleted model to allow recovery."""
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        alive_ids = model._default_manager.all().values_list("pk")
        deleted = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(self.model),
                                          action_flag=DELETION).exclude(object_id__in=alive_ids.query).order_by("action_time")
        context = {"opts": opts,
                   "app_label": app_label,
                   "module_name": capfirst(opts.verbose_name),
                   "title": _("Recover deleted %(name)s") % {"name": opts.verbose_name_plural},
                   "deleted": deleted}
        extra_context = extra_context or {}
        context.update(extra_context)
        return render_to_response(self.recover_list_template, context, RequestContext(request))
        
    def render_revision_form(self, request, obj, version, log_entry, revision, context, template, redirect_url):
        """Renders the object revision form."""
        model = self.model
        opts = model._meta
        object_id = obj.pk
        ordered_objects = opts.get_ordered_objects()
        app_label = opts.app_label
        object_version = version.object_version
        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == "POST":
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            for FormSet in self.get_formsets(request, new_object):
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object)
                formsets.append(formset)
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)
                change_message = _("Reverted to previous version, saved on %(datetime)s") % {"datetime": format(version.date_created, _(settings.DATETIME_FORMAT))}
                self.log_change(request, new_object, change_message)
                self.message_user(request, 'The %(model)s "%(name)s" was reverted successfully. You may edit it again below.' % {"model": opts.verbose_name, "name": unicode(obj)})
                return HttpResponseRedirect(redirect_url)
        else:
            form = ModelForm(instance=obj, initial=deserialized_model_to_dict(object_version, revision))
            for FormSet in self.get_formsets(request, obj):
                formset = FormSet(instance=obj)
                attname = FormSet.fk.attname
                pk_name = FormSet.model._meta.pk.name
                initial_overrides = dict(((getattr(version.object, pk_name), version) for version in revision if version.object.__class__ == FormSet.model and unicode(getattr(version.object, attname)) == unicode(object_id)))
                initial = []
                for initial_row in formset.initial:
                    pk = initial_row[pk_name]
                    if pk in initial_overrides:
                         initial_row.update(deserialized_model_to_dict(initial_overrides[pk], revision))
                         initial.append(initial_row)
                         del initial_overrides[pk]
                initial.extend([deserialized_model_to_dict(override, revision) for override in initial_overrides.values()])
                # HACK: no way to specify initial values.
                formset._total_form_count = len(initial)
                formset.initial = initial
                formset._construct_forms()
                formsets.append(formset)
        # Generate the context.
        adminForm = admin.helpers.AdminForm(form, self.get_fieldsets(request, obj), self.prepopulated_fields)
        media = self.media + adminForm.media
        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            inline_admin_formset = admin.helpers.InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
        context.update({"adminform": adminForm,
                        "object_id": obj.pk,
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
                        "form_url": mark_safe(request.path),
                        "opts": opts,
                        "content_type_id": ContentType.objects.get_for_model(self.model).id,
                        "save_as": self.save_as,
                        "save_on_top": self.save_on_top,
                        "root_path": self.admin_site.root_path,})
        return render_to_response(template, context, RequestContext(request))
        
    @revision.create_revision
    def recover_view(self, request, log_entry_id, extra_context=None):
        """Displays a form that can recover a deleted model."""
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        log_entry = get_object_or_404(LogEntry, pk=log_entry_id)
        object_id = log_entry.object_id
        content_type = ContentType.objects.get_for_model(self.model)
        try:
            version = Version.objects.filter(object_id=object_id,
                                             content_type=content_type,
                                             date_created__gte=log_entry.action_time).order_by("id")[0]
        except IndexError:
            return HttpResponseRedirect("%s%s/%s/" % (self.admin_site.root_path, app_label, model.__name__.lower()))
        obj = version.object_version.object
        revision = [version.object_version for version in version.get_revision()]
        context = {"title": _("Recover %s") % force_unicode(obj),}
        extra_context = extra_context or {}
        context.update(extra_context)
        return self.render_revision_form(request, obj, version, log_entry, revision, context, self.recover_form_template, "../../%s/" % object_id)
        
    @revision.create_revision
    def revision_view(self, request, object_id, log_entry_id, extra_context=None):
        """Displays the contents of the given revision."""
        model = self.model
        content_type = ContentType.objects.get_for_model(model)
        opts = model._meta
        app_label = opts.app_label
        obj = get_object_or_404(self.model, pk=object_id)
        log_entry = get_object_or_404(LogEntry, pk=log_entry_id)
        try:
            version = Version.objects.filter(object_id=object_id,
                                             content_type=content_type,
                                             date_created__gte=log_entry.action_time).order_by("id")[0]
        except IndexError:
            return HttpResponseRedirect("%s%s/%s/%s/" % (self.admin_site.root_path, app_label, model.__name__.lower(), object_id))
        object_version = version.object_version
        ordered_objects = opts.get_ordered_objects()
        # Generate the form.
        revision = [related_version.object_version for related_version in version.get_revision()]
        context = {"title": _("Revert %(name)s") % {"name": opts.verbose_name},}
        extra_context = extra_context or {}
        context.update(extra_context)
        return self.render_revision_form(request, obj, version, log_entry, revision, context, self.revision_form_template, "../../")
    
    # Wrap the data-modifying views in revisions.
    add_view = revision.create_revision(admin.ModelAdmin.add_view)
    change_view = revision.create_revision(admin.ModelAdmin.change_view)
    delete_view = revision.create_revision(admin.ModelAdmin.delete_view)
    
    def changelist_view(self, request, extra_context=None):
        """Renders the modified change list."""
        extra_context = extra_context or {}
        extra_context.update({"has_change_permission": self.has_change_permission(request)})
        return super(VersionAdmin, self).changelist_view(request, extra_context)
    
    def history_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        action_list = LogEntry.objects.filter(object_id = object_id,
                                              content_type__id__exact = ContentType.objects.get_for_model(self.model).id).exclude(action_flag=DELETION).select_related().order_by('action_time')
        extra_context.update({"action_list": action_list})
        return super(VersionAdmin, self).history_view(request, object_id, extra_context)