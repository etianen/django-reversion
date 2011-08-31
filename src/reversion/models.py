"""Database models used by Reversion."""

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core import serializers
from django.db import models, IntegrityError
from django.db.models import Count, Max

from reversion.errors import RevertError


class Revision(models.Model):
    
    """A group of related object versions."""
    
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
            current_revision_dict = revision.follow_relationships(old_revision_dict)
            # Delete objects that are no longer in the current revision.
            for current_object in current_revision_dict:
                if current_revision_dict[current_object] == VERSION_DELETE:
                    current_object.delete()
                    continue
                if not current_object in old_revision_dict:
                    current_object.delete()
            
    def __unicode__(self):
        """Returns a unicode representation."""
        return u", ".join([unicode(version)
                           for version in self.version_set.all()])


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
    
    def get_for_object_reference(self, model, object_id):
        """Returns all versions for the given object reference."""
        content_type = ContentType.objects.get_for_model(model)
        versions = self.filter(content_type=content_type)
        if has_int_pk(model):
            # We can do this as a fast, indexed lookup.
            object_id_int = int(object_id)
            versions = versions.filter(object_id_int=object_id_int)
        else:
            # We can't do this using an index. Never mind.
            object_id = unicode(object_id)
            versions = versions.filter(object_id=object_id)
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
        versions = self.get_for_object_reference(model_class, object_id)
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
        live_pk_queryset = model_class._default_manager.all().values_list("pk", flat=True)
        versioned_objs = self.filter(content_type=content_type)
        if has_int_pk(model_class):
            # We can do this as a fast, in-database join.
            deleted_version_pks = versioned_objs.exclude(
                object_id_int__in = live_pk_queryset
            ).values_list("object_id_int").annotate(
                latest_pk = Max("pk")
            ).values_list("latest_pk", flat=True)
            deleted = list(self.filter(pk__in=deleted_version_pks).order_by("pk"))
        else:
            # HACK: This join can't be done in the database, due to incompatibilities
            # between unicode object_ids and integer pks on strict backends like postgres.
            live_pks = frozenset(unicode(pk) for pk in live_pk_queryset.iterator())
            versioned_pks = frozenset(versioned_objs.values_list("object_id", flat=True).iterator())
            deleted_pks = (versioned_pks - live_pks)
            # Fetch all the deleted versions.
            deleted = [self.get_deleted_object(model_class, object_id, select_related) for object_id in deleted_pks]
            deleted.sort(lambda a, b: cmp(a.pk, b.pk))
        return deleted
            

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
    
    def get_object_version(self):
        """Returns the stored version of the model."""
        data = self.serialized_data
        if isinstance(data, unicode):
            data = data.encode("utf8")
        return list(serializers.deserialize(self.format, data))[0]
    
    object_version = property(get_object_version,
                              doc="The stored version of the model.")
    
    type = models.PositiveSmallIntegerField(choices=VERSION_TYPE_CHOICES, db_index=True)
       
    def get_field_dict(self):
        """
        Returns a dictionary mapping field names to field values in this version
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
       
    field_dict = property(get_field_dict,
                          doc="A dictionary mapping field names to field values in this version of the model.")
       
    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save()
        
    def __unicode__(self):
        """Returns a unicode representation."""
        return self.object_repr