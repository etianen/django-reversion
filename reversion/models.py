"""Database models used by Reversion."""


from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core import serializers
from django.db import models
from django.utils.dateformat import format

from reversion.managers import RevisionManager


class Revision(models.Model):
    
    """A group of model versions that were committed together."""
    
    objects = RevisionManager()
    
    parent = models.ForeignKey("self",
                               blank=True,
                               null=True,
                               help_text="The parent revision.")
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        help_text="When this transaction was created.")

    comment = models.TextField(blank=True,
                               null=True,
                               help_text="A comment about what took place in this revision.")

    user = models.ForeignKey("auth.User",
                             blank=True,
                             null=True,
                             help_text="The user who made this revision.")

    def __unicode__(self):
        """Returns a unicode representation."""
        return format(self.date_created, settings.DATETIME_FORMAT)


class Version(models.Model):
    
    """A saved version of a database model."""
    
    revision = models.ForeignKey("Revision",
                                 help_text="The transaction that contains this model version.")
    
    object_id = models.TextField(help_text="Primary key of the model under version control.")
    
    content_type = models.ForeignKey("contenttypes.ContentType",
                                     help_text="Content type of the model under version control.")
    
    content_object = GenericForeignKey()
    
    serialized_data = models.TextField(help_text="The serialized form of this version of the model.")
    
    def set_object_version(self, model):
        """Sets the object whose version is to be saved."""
        self.object_id = model.pk
        self.content_type = ContentType.objects.get_for_model(model)
        self.serialized_data = serializers.serialize("xml", (model,))
        
    def get_object_version(self):
        """Returns the stored version of the model."""
        return list(serializers.deserialize("xml", self.serialized_data))[0]
    
    object_version = property(get_object_version,
                              set_object_version,
                              doc="The stored version of the model.")