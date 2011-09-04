from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy as _


class ParentModel(models.Model):
    
    parent_name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.parent_name
    
    
class ChildModel(ParentModel):
    
    child_name = models.CharField(max_length=255)
    
    file = models.FileField(upload_to="test",
                            blank=True)
    
    genericrelatedmodel_set = GenericRelation("test_app.GenericRelatedModel")
    
    def __unicode__(self):
        return u"%s > %s" % (self.parent_name, self.child_name)
    
    class Meta:
        verbose_name = _("child model")
        verbose_name_plural = _("child models")
    
    
class RelatedModel(models.Model):
    
    child_model = models.ForeignKey(ChildModel)
    
    related_name = models.CharField(max_length=255)
    
    file = models.FileField(upload_to="test",
                            blank=True)
    
    def __unicode__(self):
        return self.related_name
    
    
class GenericRelatedModel(models.Model):
    
    content_type = models.ForeignKey(ContentType)
    
    object_id = models.TextField()
    
    child_model = GenericForeignKey()
    
    generic_related_name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.generic_related_name