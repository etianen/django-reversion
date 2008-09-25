"""Model managers used by Reversion."""


from django.contrib.contenttypes.models import ContentType
from django.db import models


class RevisionManager(models.Manager):
    
    """Manager for Revision models."""
    
    def get_for_object(self, obj):
        """
        Returns all the revisions that include a version of the given object.
        """
        object_id = obj.pk
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(version__object_id=object_id,
                           version__content_type=content_type).order_by("date_created")