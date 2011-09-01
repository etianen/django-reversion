"""Database models used by Reversion."""

import warnings

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core import serializers
from django.conf import settings
from django.db import models, IntegrityError
from django.db.models import Count, Max


def depricated(original, replacement):
    """Decorator that defines a depricated method."""
    def decorator(func):
        if not settings.DEBUG:
            return func
        def do_pending_deprication(*args, **kwargs):
            warnings.warn(
                "%s is depricated, use %s instead" % (original, replacement),
                PendingDeprecationWarning,
            )
            return func(*args, **kwargs)
        return do_pending_deprication
    return decorator


class RevertError(Exception):
    
    """Exception thrown when something goes wrong with reverting a model."""


class Revision(models.Model):
    
    """A group of related object versions."""
    
    manager_slug = models.CharField(
        max_length = 200,
        db_index = True,
        default = "default",
    )
    
    date_created = models.DateTimeField(auto_now_add=True,
                                        help_text="The date and time this revision was created.")
    
    user = models.ForeignKey(User,
                             blank=True,
                             null=True,
                             help_text="The user who created this revision.")
    
    comment = models.TextField(blank=True,
                               help_text="A text comment on this revision.")
    
    def revert(self, delete=False):
        """Reverts all objects in this revision."""
        # Attempt to revert all revisions.
        def do_revert(versions):
            unreverted_versions = []
            for version in versions:
                try:
                    version.revert()
                except IntegrityError:
                    unreverted_versions.append(version)
            if len(unreverted_versions) == len(versions):
                raise RevertError("Could not revert revision, due to database integrity errors.")
            if unreverted_versions:
                do_revert(unreverted_versions)
        do_revert(self.version_set.all())
        # Optionally delete objects no longer in the current revision.
        if delete:
            # Get a dict of all objects in this revision.
            old_revision_dict = dict((ContentType.objects.get_for_id(version.content_type_id).get_object_for_this_type(pk=version.object_id), version.type)
                for version in self.version_set.all())
            # Calculate the set of all objects that are in the revision now.
            from reversion import revision  # Hack: Prevents circular imports for now.
            current_revision_dict = revision._follow_relationships(old_revision_dict)
            # Delete objects that are no longer in the current revision.
            for current_object in current_revision_dict:
                if current_revision_dict[current_object] == VERSION_DELETE:
                    current_object.delete()
                    continue
                if not current_object in old_revision_dict:
                    current_object.delete()
            
    def __unicode__(self):
        """Returns a unicode representation."""
        return u", ".join(unicode(version) for version in self.version_set.all())


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
    return (
        isinstance(model._meta.pk, (models.IntegerField, models.AutoField)) and
        not isinstance(model._meta.pk, models.BigIntegerField)
    )


class VersionManager(models.Manager):
    
    """Manager for Version models."""
    
    @depricated("Version.objects.get_for_object_reference()", "reversion.get_for_object_reference()")
    def get_for_object_reference(self, model, object_id):
        """Returns all versions for the given object reference."""
        from reversion.revisions import default_revision_manager
        return default_revision_manager.get_for_object_reference(model, object_id)
    
    @depricated("Version.objects.get_for_object()", "reversion.get_for_object()")
    def get_for_object(self, object):
        """
        Returns all the versions of the given object, ordered by date created.
        """
        from reversion.revisions import default_revision_manager
        return default_revision_manager.get_for_object(object).order_by("pk")
    
    @depricated("Version.objects.get_unique_for_object()", "reversion.get_unique_for_object()")
    def get_unique_for_object(self, obj):
        """Returns unique versions associated with the object."""
        from reversion.revisions import default_revision_manager
        versions = default_revision_manager.get_unique_for_object(obj)
        versions.reverse()
        return versions
    
    @depricated("Version.objects.get_for_date()", "reversion.get_for_date()")
    def get_for_date(self, object, date):
        """Returns the latest version of an object for the given date."""
        from reversion.revisions import default_revision_manager
        return default_revision_manager.get_for_date(object, date)
    
    @depricated("Version.objects.get_deleted_object()", "reversion.get_for_object_reference()[0]")
    def get_deleted_object(self, model_class, object_id, select_related=None):
        """
        Returns the version corresponding to the deletion of the object with
        the given id.
        
        You can specify a tuple of related fields to fetch using the
        `select_related` argument.
        """
        from reversion.revisions import default_revision_manager
        return default_revision_manager.get_for_object_reference(model_class, object_id)[0]
    
    @depricated("Version.objects.get_deleted()", "reversion.get_deleted()")
    def get_deleted(self, model_class, select_related=None):
        """
        Returns all the deleted versions for the given model class.
        
        You can specify a tuple of related fields to fetch using the
        `select_related` argument.
        """
        from reversion.revisions import default_revision_manager
        return list(default_revision_manager.get_deleted(model_class, select_related))
            

class Version(models.Model):
    
    """A saved version of a database model."""
    
    objects = VersionManager()
    
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
        if isinstance(data, unicode):
            data = data.encode("utf8")
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
                    parent_id = unicode(getattr(obj, field.attname))
                else:
                    parent_id = obj.pk
                try:
                    parent_version = Version.objects.get(revision__id=self.revision_id,
                                                         content_type=content_type,
                                                         object_id=parent_id)
                except parent_class.DoesNotExist:
                    pass
                else:
                    result.update(parent_version.get_field_dict())
            setattr(self, "_field_dict_cache", result)
        return getattr(self, "_field_dict_cache")
       
    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save()
        
    def __unicode__(self):
        """Returns a unicode representation."""
        return self.object_repr