"""A number of useful helper functions to automate common tasks."""


from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from reversion.admin import VersionAdmin


def patch_admin(model, admin_site=None):
    """
    Enables version control with full admin integration for a model that has
    already been registered with the django admin site.
    
    This is excellent for adding version control to existing Django contrib
    applications. 
    """
    admin_site = admin_site or admin.site
    try:
        ModelAdmin = admin_site._registry[model].__class__
    except KeyError:
        raise NotRegistered, "The model %r has not been registered with the admin site." % model
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

    def generate_diffs(old_version, new_version, field_name, style):
        """Generates a diff array for the named field between the two versions."""
        # Extract the text from the versions.
        old_text = old_version.field_dict[field_name] or u""
        new_text = new_version.field_dict[field_name] or u""
        # Generate the patch.
        diffs = dmp.diff_main(str(old_text), str(new_text))
        if style == "semantic":
            dmp.diff_cleanupSemantic(diffs)
        if style == "efficiency":
            dmp.diff_cleanupEfficiency(diffs)
        return diffs
    
    def generate_patch(old_version, new_version, field_name, style=None):
        """
        Generates a text patch of the named field between the two versions.
        
        @param style: can be None, "semantic" or "efficiency" to cleanup the diff
        """
        diffs = generate_diffs(old_version, new_version, field_name, style)
        patch = dmp.patch_make(diffs)
        return dmp.patch_toText(patch)
    
    def generate_patch_html(old_version, new_version, field_name, style=None):
        """
        Generates a pretty html version of the differences between the named 
        field in two versions.
        
        @param style: can be None, "semantic" or "efficiency" to cleanup the diff
        """
        diffs = generate_diffs(old_version, new_version, field_name, style)
        return dmp.diff_prettyHtml(diffs)
    
