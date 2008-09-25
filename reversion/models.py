"""Database models used by Reversion."""


from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import models, transaction


class Version(models.Model):
    
    """A saved version of a database model."""
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        help_text="When this version was created.")
    
    object_id = models.TextField(help_text="Primary key of the model under version control.")
    
    content_type = models.ForeignKey("contenttypes.ContentType",
                                     help_text="Content type of the model under version control.")
    
    content_object = GenericForeignKey()
    
    transaction_start = models.ForeignKey("self",
                                          blank=True,
                                          null=True,
                                          related_name="transaction_content",
                                          help_text="The Version model that started this transaction.")
    
    serialized_data = models.TextField(help_text="The serialized form of this version of the model.")
    
    def set_object_version(self, model):
        """Sets the object whose version is to be saved."""
        self.object_id = model.pk
        self.content_type = ContentType.objects.get_for_model(model)
        self.serialized_data = serializers.serialize("xml", (model,))
        
    def get_object_version(self):
        """Returns the stored version of the model."""
        return serializers.deserialize("xml", self.serialized_data)
    
    object_version = property(get_object_version,
                              set_object_version,
                              doc="The stored version of the model.")
    
    def revert(self):
        """Reverts the model data to this version."""
        self.object_version.save()
        
    def get_transaction(self):
        """Returns a list of all model versions in this transaction."""
        if self.transaction_start:
            return self.transaction_start.get_transaction()
        return [self] + self.transaction_content
        
    @transaction.commit_on_success
    def revert_transaction(self):
        """Reverts all models in this transaction."""
        for version in self.get_transaction():
            version.revert()
        
    class Meta:
        ordering = "pk",