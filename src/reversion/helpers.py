"""A number of useful helper functions to automate common tasks."""


from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.db import models
from django.db.models.query import QuerySet  
from django.forms.models import model_to_dict

from reversion.registration import get_registration_info


def add_to_revision(instance, revision_set):
    """
    Calculates the objects that should be included in the same revision as the
    given instance.
    
    All calculated objects are added to the `revision_set`.
    """
    # Prevent recursion.
    if instance in revision_set:
        return
    revision_set.add(instance)
    # Follow relations.
    fields, follow, format = get_registration_info(instance.__class__)
    if follow:
        for relationship in follow:
            try:
                # Clear foreign key cache.
                related_field = instance._meta.get_field(relationship)
                if isinstance(related_field, models.ForeignKey):
                    if hasattr(instance, related_field.get_cache_name()):
                        delattr(instance, related_field.get_cache_name())
            except models.FieldDoesNotExist:
                pass
            related = getattr(instance, relationship, None)
            if isinstance(related, models.Model):
                add_to_revision(related, revision_set) 
            elif isinstance(related, (models.Manager, QuerySet)):
                for related_obj in related.all():
                    add_to_revision(related_obj, revision_set)
            elif related is not None:
                raise TypeError, "Cannot follow the relationship '%s', unexpected type %s" % (relationship, type(related).__name__)
    

def deserialized_model_to_dict(deserialized_model, revision_data):
    """
    Converts a deserialized model to a dictionary.
    
    In order to properly follow any parent links, this method requires that the
    full revision data is also specified.
    """
    model = deserialized_model.object
    result = model_to_dict(model)
    result.update(deserialized_model.m2m_data)
    # Add parent data.
    for parent_class, field in model._meta.parents.items():
        attname = field.attname
        attvalue = getattr(model, attname)
        pk_name = parent_class._meta.pk.attname
        for deserialized_model in revision_data:
            parent = deserialized_model.object
            if parent_class == parent.__class__ and unicode(getattr(parent, pk_name)) == unicode(getattr(model, attname)):
                result.update(deserialized_model_to_dict(deserialized_model, revision_data))
    return result


def version_to_dict(version):
    """
    Returns the serialiazed model contained in the version as dictionary of
    property names and values.
    """
    revision = version.revision
    object_version = version.object_version
    return deserialized_model_to_dict(object_version, revision)


def patch_admin(model, admin_site=None):
    """
    Enables version control with full admin integration for a model that has
    already been registered with the django admin site.
    
    This is excellent for adding version control to existing Django contrib
    applications. 
    """
    from reversion.admin import VersionAdmin
    admin_site = admin_site or admin.site
    try:
        ModelAdmin = admin_site._registry[model].__class__
    except KeyError:
        raise NotRegistered, "The model %s has not been registered with the admin site." % model
    # Unregister existing admin class.
    admin_site.unregister(model)
    # Register patched admin class.
    class PatchedModelAdmin(VersionAdmin, ModelAdmin):
        pass
    admin_site.register(model, PatchedModelAdmin)


# Patch generation methods, only available if the google-diff-match-patch
# library is installed.
#
# http://code.google.com/p/google-diff-match-patch/

try:
    from diff_match_patch import diff_match_patch
except ImportError:
    pass 
else:
    dmp = diff_match_patch()
    
    def generate_diffs(old_version, new_version, field_name):
        """
        Generates a diff array of the named field between the two versions.
        """
        # Extract the text from the versions.
        old_dict = version_to_dict(old_version)
        new_dict = version_to_dict(new_version)
        old_text = old_dict[field_name]
        new_text = new_dict[field_name]
        # Generate the patch.
        diffs = dmp.diff_main(old_text, new_text)
        return diffs
    
    def generate_patch(old_version, new_version, field_name):
        """
        Generates a text patch of the named field between the two versions.
        """
        diffs = generate_diffs(old_version, new_version, field_name)
        patch = dmp.patch_make(diffs)
        return dmp.patch_toText(patch)
        
    def generate_patch_html(old_version, new_version, field_name):
        """
        Generates a pretty html version of the differences between the named 
        field in two versions.
        """
        diffs = generate_diffs(old_version, new_version, field_name)
        return dmp.diff_prettyHtml(diffs)
    
    