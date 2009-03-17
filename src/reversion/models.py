"""Database models used by Reversion."""


try:
    set
except NameError:
    from sets import Set as set  # Python 2.3 fallback.

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import models

from reversion.helpers import add_to_revision
from reversion.managers import VersionManager
from reversion.registration import get_registration_info


class Revision(models.Model):
    
    """A group of related object versions."""
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        help_text="The date and time this revision was created.")

    user = models.ForeignKey(User,
                             blank=True,
                             null=True,
                             help_text="The user who created this revision.")
    
    comment = models.TextField(blank=True,
                               null=True,
                               help_text="A text comment on this revision.")
    
    def revert(self, delete=False):
        """Reverts all objects in this revision."""
        versions = self.version_set.all()
        for version in versions:
            version.revert()
        if delete:
            # Get a set of all objects in this revision.
            old_revision_set = set([version.latest_object_version for version in versions])
            # Calculate the set of all objects that would be in the revision now.
            current_revision_set = set()
            for latest_object_version in old_revision_set:
                add_to_revision(latest_object_version, current_revision_set)
            for current_object in current_revision_set:
                if not current_object in old_revision_set:
                    current_object.delete()
            
    def __unicode__(self):
        """Returns a unicode representation."""
        return u", ".join([unicode(version)
                           for version in self.version_set.all()])
            

class Version(models.Model):
    
    """A saved version of a database model."""
    
    objects = VersionManager()
    
    revision = models.ForeignKey(Revision,
                                 help_text="The revision that contains this version.")
    
    object_id = models.TextField(help_text="Primary key of the model under version control.")
    
    content_type = models.ForeignKey(ContentType,
                                     help_text="Content type of the model under version control.")
    
    format = models.CharField(max_length=255,
                              help_text="The serialization format used by this model.")
    
    serialized_data = models.TextField(help_text="The serialized form of this version of the model.")
    
    object_repr = models.TextField(help_text="A string representation of the object.")
    
    def get_object_version(self):
        """Returns the stored version of the model."""
        data = self.serialized_data
        if isinstance(data, unicode):
            data = data.encode("utf8")
        return list(serializers.deserialize(self.format, data))[0]
    
    object_version = property(get_object_version,
                              doc="The stored version of the model.")
       
    def get_latest_object_version(self):
        """
        Returns the latest version of the stored object.
        
        If the object no longer exists, returns None.
        """
        model_class = self.content_type.model_class()
        try:
            return model_class._default_manager.get(pk=self.object_id)
        except model_class.DoesNotExist:
            return None
        
    latest_object_version = property(get_latest_object_version,
                              doc="The latest version of the model.")
       
    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save()
        
    def __unicode__(self):
        """Returns a unicode representation."""
        return self.object_repr
    
    