"""Database models used by Reversion."""


from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core import serializers
from django.db import models
from django.db.models.signals import class_prepared, post_save, pre_delete

from reversion.managers import VersionManager


class Version(models.Model):
    
    """A saved version of a database model."""
    
    objects = VersionManager()
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        help_text="The date and time this version was created.")
    
    revision_start = models.ForeignKey("self",
                                       blank=True,
                                       null=True,
                                       related_name="revision_content",
                                       help_text="The Version that started this transaction.")
    
    object_id = models.TextField(help_text="Primary key of the model under version control.")
    
    content_type = models.ForeignKey("contenttypes.ContentType",
                                     help_text="Content type of the model under version control.")
    
    content_object = GenericForeignKey()
    
    serialized_data = models.TextField(help_text="The serialized form of this version of the model.")
    
    def get_object_version(self):
        """Returns the stored version of the model."""
        return list(serializers.deserialize("xml", self.serialized_data))[0]
    
    object_version = property(get_object_version,
                              doc="The stored version of the model.")
    
    def get_revision(self):
        """Returns all the versions in the given revision."""
        if self.revision_start:
            return self.revision_start.get_revision()
        return [self] + list(self.revision_content.all().order_by("pk"))
    
    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save()
    
    def revert_revision(self):
        """Recovers all models of all versions in this revision."""
        for version in self.get_revision():
            version.revert()
    
    def __unicode__(self):
        """Returns a unicode representation."""
        return unicode(self.get_object_version().object)


from reversion.receivers import save_version, save_deleted_version


post_save.connect(save_version)
pre_delete.connect(save_deleted_version)
    

