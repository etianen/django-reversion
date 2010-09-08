"""Model managers for Reversion."""


from django.contrib.contenttypes.models import ContentType
from django.db import models


class VersionManager(models.Manager):
    
    """Manager for Version models."""
    
    def get_for_object_reference(self, model, object_id):
        """Returns all versions for the given object reference."""
        content_type = ContentType.objects.get_for_model(model)
        object_id = unicode(object_id)
        versions = self.filter(content_type=content_type, object_id=object_id)
        versions = versions.order_by("pk")
        return versions
    
    def get_for_object(self, object):
        """
        Returns all the versions of the given object, ordered by date created.
        """
        return self.get_for_object_reference(object.__class__, object.pk)
    
    def get_unique_for_object(self,obj):
        """Returns unique versions associated with the object."""
        versions = self.get_for_object(obj)
        changed_versions = []
        last_serialized_data = None
        for version in versions:
            if last_serialized_data != version.serialized_data:
                changed_versions.append(version)
            last_serialized_data = version.serialized_data
        return changed_versions
    
    def get_for_date(self, object, date):
        """Returns the latest version of an object for the given date."""
        versions = self.get_for_object(object)
        versions = versions.filter(revision__date_created__lte=date)
        versions = versions.order_by("-pk")
        try:
            version = versions[0]
        except IndexError:
            raise self.model.DoesNotExist
        else:
            return version
    
    def get_deleted_object(self, model_class, object_id, select_related=None):
        """
        Returns the version corresponding to the deletion of the object with
        the given id.
        
        You can specify a tuple of related fields to fetch using the
        `select_related` argument.
        """
        # Ensure that the revision is in the select_related tuple.
        select_related = select_related or ()
        if not "revision" in select_related:
            select_related = tuple(select_related) + ("revision",)
        # Fetch the version.
        content_type = ContentType.objects.get_for_model(model_class)
        object_id = unicode(object_id)
        versions = self.filter(content_type=content_type, object_id=object_id)
        versions = versions.order_by("-pk")
        if select_related:
            versions = versions.select_related(*select_related)
        try:
            version = versions[0]
        except IndexError:
            raise self.model.DoesNotExist
        else:
            return version
    
    def get_deleted(self, model_class, select_related=None):
        """
        Returns all the deleted versions for the given model class.
        
        You can specify a tuple of related fields to fetch using the
        `select_related` argument.
        """
        content_type = ContentType.objects.get_for_model(model_class)
        deleted = []
        # HACK: This join can't be done in the database, due to incompatibilities
        # between unicode object_ids and integer pks on strict backends like postgres.
        for object_id in self.filter(content_type=content_type).values_list("object_id", flat=True).distinct().iterator():
            if model_class._default_manager.filter(pk=object_id).count() == 0:
                deleted.append(self.get_deleted_object(model_class, object_id, select_related))
        deleted.sort(lambda a, b: cmp(a.revision.date_created, b.revision.date_created))
        return deleted
        
        