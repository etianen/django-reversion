"""Database models used by django-reversion."""

from __future__ import unicode_literals

import warnings
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, IntegrityError
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import Signal, _make_id
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible


def safe_revert(versions):
    """
    Attempts to revert the given models contained in the give versions.
    
    This method will attempt to resolve dependencies between the versions to revert
    them in the correct order to avoid database integrity errors.
    """
    unreverted_versions = []
    for version in versions:
        try:
            version.revert()
        except (IntegrityError, ObjectDoesNotExist):
            unreverted_versions.append(version)
    if len(unreverted_versions) == len(versions):
        raise RevertError("Could not revert revision, due to database integrity errors.")
    if unreverted_versions:
        safe_revert(unreverted_versions)


class RevertError(Exception):
    
    """Exception thrown when something goes wrong with reverting a model."""


UserModel = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


@python_2_unicode_compatible
class Revision(models.Model):
    
    """A group of related object versions."""
    
    manager_slug = models.CharField(
        max_length = 200,
        db_index = True,
        default = "default",
    )
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        verbose_name=_("date created"),
                                        help_text="The date and time this revision was created.")
    
    user = models.ForeignKey(UserModel,
                             blank=True,
                             null=True,
                             verbose_name=_("user"),
                             help_text="The user who created this revision.")
    
    comment = models.TextField(blank=True,
                               verbose_name=_("comment"),
                               help_text="A text comment on this revision.")
    
    def revert(self, delete=False):
        """Reverts all objects in this revision."""
        version_set = self.version_set.all()
        # Optionally delete objects no longer in the current revision.
        if delete:
            # Get a dict of all objects in this revision.
            old_revision = {}
            for version in version_set:
                try:
                    obj = version.object
                except ContentType.objects.get_for_id(version.content_type_id).model_class().DoesNotExist:
                    pass
                else:
                    old_revision[obj] = version
            # Calculate the set of all objects that are in the revision now.
            from reversion.revisions import RevisionManager
            current_revision = RevisionManager.get_manager(self.manager_slug)._follow_relationships(obj for obj in old_revision.keys() if obj is not None)
            # Delete objects that are no longer in the current revision.
            for item in current_revision:
                if item in old_revision:
                    if old_revision[item].type == VERSION_DELETE:
                        item.delete()
                else:
                    item.delete()
        # Attempt to revert all revisions.
        safe_revert([version for version in version_set if version.type != VERSION_DELETE])
        
    def __str__(self):
        """Returns a unicode representation."""
        return ", ".join(force_text(version) for version in self.version_set.all())


# Version types.

VERSION_ADD = 0
VERSION_CHANGE = 1
VERSION_DELETE = 2

VERSION_TYPE_CHOICES = (
    (VERSION_ADD, "Addition"),
    (VERSION_CHANGE, "Change"),
    (VERSION_DELETE, "Deletion"),
)

def has_int_pk(model):
    """Tests whether the given model has an integer primary key."""
    pk = model._meta.pk
    return (
        (
            isinstance(pk, (models.IntegerField, models.AutoField)) and
            not isinstance(pk, models.BigIntegerField)
        ) or (
            isinstance(pk, models.ForeignKey) and has_int_pk(pk.rel.to)
        )
    )
            

@python_2_unicode_compatible
class Version(models.Model):
    
    """A saved version of a database model."""
    
    revision = models.ForeignKey(Revision,
                                 help_text="The revision that contains this version.")
    
    object_id = models.TextField(help_text="Primary key of the model under version control.")
    
    object_id_int = models.IntegerField(
        blank = True,
        null = True,
        db_index = True,
        help_text = "An indexed, integer version of the stored model's primary key, used for faster lookups.",
    )
    
    content_type = models.ForeignKey(ContentType,
                                     help_text="Content type of the model under version control.")
    
    # A link to the current instance, not the version stored in this Version!
    object = generic.GenericForeignKey()
    
    format = models.CharField(max_length=255,
                              help_text="The serialization format used by this model.")
    
    serialized_data = models.TextField(help_text="The serialized form of this version of the model.")
    
    object_repr = models.TextField(help_text="A string representation of the object.")
    
    @property
    def object_version(self):
        """The stored version of the model."""
        data = self.serialized_data
        data = force_text(data.encode("utf8"))
        return list(serializers.deserialize(self.format, data))[0]
    
    type = models.PositiveSmallIntegerField(choices=VERSION_TYPE_CHOICES, db_index=True)
    
    @property   
    def field_dict(self):
        """
        A dictionary mapping field names to field values in this version
        of the model.
        
        This method will follow parent links, if present.
        """
        if not hasattr(self, "_field_dict_cache"):
            object_version = self.object_version
            obj = object_version.object
            result = {}
            for field in obj._meta.fields:
                result[field.name] = field.value_from_object(obj)
            result.update(object_version.m2m_data)
            # Add parent data.
            for parent_class, field in obj._meta.parents.items():
                content_type = ContentType.objects.get_for_model(parent_class)
                if field:
                    parent_id = force_text(getattr(obj, field.attname))
                else:
                    parent_id = obj.pk
                try:
                    parent_version = Version.objects.get(revision__id=self.revision_id,
                                                         content_type=content_type,
                                                         object_id=parent_id)
                except Version.DoesNotExist:
                    pass
                else:
                    result.update(parent_version.field_dict)
            setattr(self, "_field_dict_cache", result)
        return getattr(self, "_field_dict_cache")
       
    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save()
    
    def __str__(self):
        """Returns a unicode representation."""
        return self.object_repr


# Version management signals.
pre_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
post_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
    

def check_for_receivers(sender, sending_signal, **kwargs):
    """Checks that no other signal receivers have been connected."""
    if len(sending_signal._live_receivers(_make_id(sender))) > 1:
        warnings.warn("pre_save and post_save signals will not longer be sent for Revision and Version models in django-reversion 1.8. Please use the pre_revision_commit and post_revision_commit signals instead.")

check_for_pre_save_receivers = partial(check_for_receivers, sending_signal=pre_save)
check_for_post_save_receivers = partial(check_for_receivers, sending_signal=post_save) 

pre_save.connect(check_for_pre_save_receivers, sender=Revision)
pre_save.connect(check_for_pre_save_receivers, sender=Version)
post_save.connect(check_for_post_save_receivers, sender=Revision)
post_save.connect(check_for_post_save_receivers, sender=Version)
