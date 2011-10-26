"""Admin extensions for django-reversion."""

from django import template
from django.db import models, transaction
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.admin import helpers, options
from django.contrib.admin.util import unquote
from django.contrib.contenttypes.generic import GenericInlineModelAdmin, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.forms.formsets import all_valid
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.dateformat import format
from django.utils.html import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode

from reversion.models import Version
from reversion.revisions import revision_context_manager, default_revision_manager


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
    
    def _autoregister(self, model, follow=None):
        """Registers a model with reversion, if required."""
        if not self.revision_manager.is_registered(model):
            follow = follow or []
            for parent_cls, field in model._meta.parents.items():
                follow.append(field.name)
                self._autoregister(parent_cls)
            self.revision_manager.register(model, follow=follow, format=self.reversion_format)
    
    def __init__(self, *args, **kwargs):
        """Initializes the VersionAdmin"""
        super(VersionAdmin, self).__init__(*args, **kwargs)
        # Automatically register models if required.
        if not self.revision_manager.is_registered(self.model):
            inline_fields = []
            for inline in self.inlines:
                inline_model = inline.model
                self._autoregister(inline_model)
                if issubclass(inline, GenericInlineModelAdmin):
                    ct_field = inline.ct_field
                    ct_fk_field = inline.ct_fk_field
                    for field in self.model._meta.many_to_many:
                        if isinstance(field, GenericRelation) and field.rel.to == inline_model and field.object_id_field_name == ct_fk_field and field.content_type_field_name == ct_field:
                            inline_fields.append(field.name)
                elif issubclass(inline, options.InlineModelAdmin):
                    fk_name = inline.fk_name
                    if not fk_name:
                        for field in inline_model._meta.fields:
                            if isinstance(field, (models.ForeignKey, models.OneToOneField)) and issubclass(self.model, field.rel.to):
                                fk_name = field.name
                    accessor = inline_model._meta.get_field(fk_name).related.get_accessor_name()
                    inline_fields.append(accessor)
            self._autoregister(self.model, inline_fields)

    def _get_template_list(self, template_name):
        opts = self.model._meta
        return (
            "reversion/%s/%s/%s" % (opts.app_label, opts.object_name.lower(), template_name),
            "reversion/%s/%s" % (opts.app_label, template_name),
            "reversion/%s" % template_name,
        )
    
    def get_urls(self):
        """Returns the additional urls used by the Reversion admin."""
        urls = super(VersionAdmin, self).get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.module_name,
        reversion_urls = patterns("",
                                  url("^recover/$", admin_site.admin_view(self.recoverlist_view), name='%s_%s_recoverlist' % info),
                                  url("^recover/([^/]+)/$", admin_site.admin_view(self.recover_view), name='%s_%s_recover' % info),
                                  url("^([^/]+)/history/([^/]+)/$", admin_site.admin_view(self.revision_view), name='%s_%s_revision' % info),)
        return reversion_urls + urls
    
    def log_addition(self, request, object):
        """Sets the version meta information."""
        super(VersionAdmin, self).log_addition(request, object)
        revision_context_manager.set_user(request.user)
        revision_context_manager.set_comment(_(u"Initial version."))
        revision_context_manager.set_ignore_duplicates(self.ignore_duplicate_revisions)
        
    def log_change(self, request, object, message):
        """Sets the version meta information."""
        super(VersionAdmin, self).log_change(request, object, message)
        revision_context_manager.set_user(request.user)
        revision_context_manager.set_comment(message)
        revision_context_manager.set_ignore_duplicates(self.ignore_duplicate_revisions)
    
    def log_deletion(self, request, object, object_repr):
        """Sets the version meta information."""
        super(VersionAdmin, self).log_deletion(request, object, object_repr)
        revision_context_manager.set_user(request.user)
        revision_context_manager.set_comment(_(u"Deleted %(verbose_name)s.") % {"verbose_name": self.model._meta.verbose_name})
        revision_context_manager.set_ignore_duplicates(self.ignore_duplicate_revisions)
    
    def _order_version_queryset(self, queryset):
        """Applies the correct ordering to the given version queryset."""
        if self.history_latest_first:
            return queryset.order_by("-pk")
        return queryset.order_by("pk")
    
    def recoverlist_view(self, request, extra_context=None):
        """Displays a deleted model to allow recovery."""
        model = self.model
        opts = model._meta
        deleted = self._order_version_queryset(self.revision_manager.get_deleted(self.model))
        context = {
            "opts": opts,
            "app_label": opts.app_label,
            "module_name": capfirst(opts.verbose_name),
            "title": _("Recover deleted %(name)s") % {"name": force_unicode(opts.verbose_name_plural)},
            "deleted": deleted,
            "changelist_url": reverse("%s:%s_%s_changelist" % (self.admin_site.name, opts.app_label, opts.module_name)),
        }
        extra_context = extra_context or {}
        context.update(extra_context)
        return render_to_response(self.recover_list_template or self._get_template_list("recover_list.html"),
            context, template.RequestContext(request))
        
    def get_revision_form_data(self, request, obj, version):
        """
        Returns a dictionary of data to set in the admin form in order to revert
        to the given revision.
        """
        return version.field_dict
    
    def get_related_versions(self, obj, version, FormSet):
        """Retreives all the related Version objects for the given FormSet."""
        object_id = obj.pk
        # Get the fk name.
        try:
            fk_name = FormSet.fk.name
        except AttributeError:
            # This is a GenericInlineFormset, or similar.
            fk_name = FormSet.ct_fk_field.name
        # Look up the revision data.
        revision_versions = version.revision.version_set.all()
        related_versions = dict([(related_version.object_id, related_version)
                                 for related_version in revision_versions
                                 if ContentType.objects.get_for_id(related_version.content_type_id).model_class() == FormSet.model
                                 and unicode(related_version.field_dict[fk_name]) == unicode(object_id)])
        return related_versions
    
    def _hack_inline_formset_initial(self, FormSet, formset, obj, version, revert, recover):
        """Hacks the given formset to contain the correct initial data."""
        # Now we hack it to push in the data from the revision!
        initial = []
        related_versions = self.get_related_versions(obj, version, FormSet)
        formset.related_versions = related_versions
        for related_obj in formset.queryset:
            if unicode(related_obj.pk) in related_versions:
                initial.append(related_versions.pop(unicode(related_obj.pk)).field_dict)
            else:
                initial_data = model_to_dict(related_obj)
                initial_data["DELETE"] = True
                initial.append(initial_data)
        for related_version in related_versions.values():
            initial_row = related_version.field_dict
            pk_name = ContentType.objects.get_for_id(related_version.content_type_id).model_class()._meta.pk.name
            del initial_row[pk_name]
            initial.append(initial_row)
        # Reconstruct the forms with the new revision data.
        formset.initial = initial
        formset.forms = [formset._construct_form(n) for n in xrange(len(initial))]
        # Hack the formset to force a save of everything.
        for form in formset.forms:
            form.has_changed = lambda: True
            form._get_changed_data = lambda: [field.name for field in form.fields]  # TODO: Scope this in a partial function.
        def total_form_count_hack(count):
            return lambda: count
        formset.total_form_count = total_form_count_hack(len(initial))
    
    def render_revision_form(self, request, obj, version, context, revert=False, recover=False):
        """Renders the object revision form."""
        model = self.model
        opts = model._meta
        object_id = obj.pk
        # Generate the model form.
        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == "POST":
            # This section is copied directly from the model admin change view
            # method.  Maybe one day there will be a hook for doing this better.
            form = ModelForm(request.POST, request.FILES, instance=obj, initial=self.get_revision_form_data(request, obj, version))
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
                # HACK: If the value of a file field is None, remove the file from the model.
                for field in new_object._meta.fields:
                    if isinstance(field, models.FileField) and field.name in form.cleaned_data and form.cleaned_data[field.name] is None:
                        setattr(new_object, field.name, None)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, new_object),
                                       self.inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix,
                                  queryset=inline.queryset(request))
                self._hack_inline_formset_initial(FormSet, formset, obj, version, revert, recover)
                # Add this hacked formset to the form.
                formsets.append(formset)
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    # HACK: If the value of a file field is None, remove the file from the model.
                    related_objects = formset.save(commit=False)
                    for related_obj, related_form in zip(related_objects, formset.saved_forms):
                        for field in related_obj._meta.fields:
                            if isinstance(field, models.FileField) and field.name in related_form.cleaned_data and related_form.cleaned_data[field.name] is None:
                                setattr(related_obj, field.name, None)
                        related_obj.save()
                    formset.save_m2m()
                change_message = _(u"Reverted to previous version, saved on %(datetime)s") % {"datetime": format(version.revision.date_created, _('DATETIME_FORMAT'))}
                self.log_change(request, new_object, change_message)
                self.message_user(request, _(u'The %(model)s "%(name)s" was reverted successfully. You may edit it again below.') % {"model": force_unicode(opts.verbose_name), "name": unicode(obj)})
                # Redirect to the model change form.
                if revert:
                    return HttpResponseRedirect("../../")
                elif recover:
                    return HttpResponseRedirect("../../%s/" % object_id)
                else:
                    assert False
        else:
            # This is a mutated version of the code in the standard model admin
            # change_view.  Once again, a hook for this kind of functionality
            # would be nice.  Unfortunately, it results in doubling the number
            # of queries required to construct the formets.
            form = ModelForm(instance=obj, initial=self.get_revision_form_data(request, obj, version))
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, obj), self.inline_instances):
                # This code is standard for creating the formset.
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix,
                                  queryset=inline.queryset(request))
                self._hack_inline_formset_initial(FormSet, formset, obj, version, revert, recover)
                # Add this hacked formset to the form.
                formsets.append(formset)
        # Generate admin form helper.
        adminForm = helpers.AdminForm(form, self.get_fieldsets(request, obj),
            self.prepopulated_fields, self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media
        # Generate formset helpers.
        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
        # Generate the context.
        context.update({"adminform": adminForm,
                        "object_id": object_id,
                        "original": obj,
                        "is_popup": False,
                        "media": mark_safe(media),
                        "inline_admin_formsets": inline_admin_formsets,
                        "errors": helpers.AdminErrorList(form, formsets),
                        "app_label": opts.app_label,
                        "add": False,
                        "change": True,
                        "revert": revert,
                        "recover": recover,
                        "has_add_permission": self.has_add_permission(request),
                        "has_change_permission": self.has_change_permission(request, obj),
                        "has_delete_permission": self.has_delete_permission(request, obj),
                        "has_file_field": True,
                        "has_absolute_url": False,
                        "ordered_objects": opts.get_ordered_objects(),
                        "form_url": mark_safe(request.path),
                        "opts": opts,
                        "content_type_id": ContentType.objects.get_for_model(self.model).id,
                        "save_as": False,
                        "save_on_top": self.save_on_top,
                        "changelist_url": reverse("%s:%s_%s_changelist" % (self.admin_site.name, opts.app_label, opts.module_name)),
                        "change_url": reverse("%s:%s_%s_change" % (self.admin_site.name, opts.app_label, opts.module_name), args=(obj.pk,)),
                        "history_url": reverse("%s:%s_%s_history" % (self.admin_site.name, opts.app_label, opts.module_name), args=(obj.pk,)),
                        "recoverlist_url": reverse("%s:%s_%s_recoverlist" % (self.admin_site.name, opts.app_label, opts.module_name))})
        # Render the form.
        if revert:
            form_template = self.revision_form_template or self._get_template_list("revision_form.html")
        elif recover:
            form_template = self.recover_form_template or self._get_template_list("recover_form.html")
        else:
            assert False
        return render_to_response(form_template, context, template.RequestContext(request))
    
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def recover_view(self, request, version_id, extra_context=None):
        """Displays a form that can recover a deleted model."""
        version = get_object_or_404(Version, pk=version_id)
        obj = version.object_version.object
        context = {"title": _("Recover %(name)s") % {"name": version.object_repr},}
        context.update(extra_context or {})
        return self.render_revision_form(request, obj, version, context, recover=True)
        
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def revision_view(self, request, object_id, version_id, extra_context=None):
        """Displays the contents of the given revision."""
        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        obj = get_object_or_404(self.model, pk=object_id)
        version = get_object_or_404(Version, pk=version_id, object_id=unicode(obj.pk))
        # Generate the context.
        context = {"title": _("Revert %(name)s") % {"name": force_unicode(self.model._meta.verbose_name)},}
        context.update(extra_context or {})
        return self.render_revision_form(request, obj, version, context, revert=True)
    
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def add_view(self, *args, **kwargs):
        """Adds a new model to the application."""
        return super(VersionAdmin, self).add_view(*args, **kwargs)
    
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def change_view(self, *args, **kwargs):
        """Modifies an existing model."""
        return super(VersionAdmin, self).change_view(*args, **kwargs)
        
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def delete_view(self, *args, **kwargs):
        """Deletes an existing model."""
        return super(VersionAdmin, self).delete_view(*args, **kwargs)
    
    @transaction.commit_on_success
    @revision_context_manager.create_revision()
    def changelist_view(self, request, extra_context=None):
        """Renders the change view."""
        opts = self.model._meta
        context = {"recoverlist_url": reverse("%s:%s_%s_recoverlist" % (self.admin_site.name, opts.app_label, opts.module_name)),
                   "add_url": reverse("%s:%s_%s_add" % (self.admin_site.name, opts.app_label, opts.module_name)),}
        context.update(extra_context or {})
        return super(VersionAdmin, self).changelist_view(request, context)
    
    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        opts = self.model._meta
        action_list = [
            {
                "revision": version.revision,
                "url": reverse("%s:%s_%s_revision" % (self.admin_site.name, opts.app_label, opts.module_name), args=(version.object_id, version.id)),
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
