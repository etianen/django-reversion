"""Admin extensions for Reversion."""


from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from reversion import revision
from reversion.models import Revision


class VersionAdmin(admin.ModelAdmin):
    
    """Abstract admin class for handling version controlled models."""

    object_history_template = "reversion/object_history.html"
    
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
        content_type = ContentType.objects.get_for_model(self.model)
        action_list = Revision.objects.filter(version__object_id=object_id,
                                              version__content_type=content_type).order_by("date_created")
        context = {"action_list": action_list,}
        if extra_context:
            context.update(extra_context)
        return super(VersionAdmin, self).history_view(request, object_id, context)