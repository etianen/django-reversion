from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models

import reversion
from reversion.helpers import patch_admin


class ParentModel(models.Model):
    
    parent_name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.parent_name
    
    
class ChildModel(ParentModel):
    
    child_name = models.CharField(max_length=255)
    
    file = models.FileField(upload_to="test")
    
    def __unicode__(self):
        return u"%s > %s" % (self.parent_name, self.child_name)
    
    
class RelatedModel(models.Model):
    
    child_model = models.ForeignKey(ChildModel)
    
    related_name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.related_name
    
    
class GenericRelatedModel(models.Model):
    
    content_type = models.ForeignKey(ContentType)
    
    object_id = models.TextField()
    
    generic_related_name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.generic_related_name
    
    
class ProxyModel(ChildModel):
    
    class Meta:
        proxy = True
        
        