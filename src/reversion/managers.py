"""Model managers for Reversion."""


from django.contrib.contenttypes.models import ContentType
from django.db import models


class VersionManager(models.Manager):
    
    """Manager for Version models."""
    
    def get_for_object(self, object):
        """Returns all the versions of the given, ordered by date created."""
        content_type = ContentType.objects.get_for_model(object)
        return self.filter(content_type=content_type, object_id=object.pk).order_by("pk")
    
    def get_for_date(self, object, date):
        """Returns the latest version of an object for the given date."""
        try:
            return self.get_for_object(object).filter(date_created__lte=date).order_by("-pk")[0]
        except IndexError:
            raise self.model.DoesNotExist
    
    def get_deleted(self, model_class):
        """Returns all the deleted objects for the given model class."""
        live_objects = model_class._default_manager.all().values_list("pk")
        content_type = ContentType.objects.get_for_model(model_class)
        return self.filter(content_type=content_type).exclude(pk__in=live_objects.query).order_by("pk")
    
    def get_deleted_object(self, model_class, object_id):
        """
        Returns the revision corresponding to the deletion of the object with
        the given id.
        """
        try:
            return self.get_deleted(model_class).filter(object_id=object_id).order_by("-pk")[0]
        except IndexError:
            raise self.model.DoesNotExist