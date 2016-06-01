from __future__ import unicode_literals
from collections import defaultdict
from itertools import chain
from django.contrib.contenttypes.models import ContentType
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:  # Django < 1.9 pragma: no cover
    from django.contrib.contenttypes.generic import GenericForeignKey
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, IntegrityError, transaction
from django.db.models.lookups import In
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible
from reversion.errors import RevertError
from reversion.revisions import RevisionManager, default_revision_manager
from reversion.signals import pre_revision_commit, post_revision_commit, post_revision_context_end


def safe_revert(versions):
    """
    Attempts to revert the given models contained in the give versions.

    This method will attempt to resolve dependencies between the versions to revert
    them in the correct order to avoid database integrity errors.
    """
    unreverted_versions = []
    for version in versions:
        try:
            with transaction.atomic(using=version.db):
                version.revert()
        except (IntegrityError, ObjectDoesNotExist):
            unreverted_versions.append(version)
    if len(unreverted_versions) == len(versions):
        raise RevertError("Could not revert revision, due to database integrity errors.")
    if unreverted_versions:
        safe_revert(unreverted_versions)


class RevisionQuerySet(models.QuerySet):

    def for_revision_manager(self, revision_manager):
        """
        Returns all revisions created using the given revision manager.
        """
        return self.filter(manager_slug=revision_manager._manager_slug)


class RevisionModelManager(models.Manager):

    def save_revision(self, objects=(), serialized_objects=(), ignore_duplicates=False, user=None, comment="", meta=(),
                      revision_manager=default_revision_manager):
        """
        Manually saves a new revision containing the given objects.

        `objects` is an iterable of model instances.
        `serialized_objects` is an iterable of dicts of version data.
        """
        # Create the object versions.
        version_data_dict = {
            (
                version_data["app_label"],
                version_data["model_name"],
                version_data["object_id"],
            ): version_data
            for version_data
            in serialized_objects
        }
        for obj in objects:
            for relation in revision_manager._follow_relationships(obj):
                adapter = revision_manager.get_adapter(relation.__class__)
                version_data = adapter.get_version_data(relation)
                version_data_dict[(
                    version_data["app_label"],
                    version_data["model_name"],
                    version_data["object_id"],
                )] = version_data
        new_versions = [
            Version(
                content_type=ContentType.objects.db_manager(self.db).get_by_natural_key(
                    version_data["app_label"],
                    version_data["model_name"],
                ),
                object_id=version_data["object_id"],
                db=version_data["db"],
                format=version_data["format"],
                serialized_data=version_data["serialized_data"],
                object_repr=version_data["object_repr"],
            )
            for version_data
            in version_data_dict.values()
        ]
        # Bail early if there are no objects to save.
        if not new_versions:
            return
        # Check for duplicates, if requested.
        save_revision = True
        if ignore_duplicates:
            # Find the latest revision amongst the latest previous version of each object.
            latest_revision_qs = self.annotate(
                version_count=models.Count("version"),
            ).filter(
                version_count=len(new_versions),
                manager_slug=revision_manager._manager_slug,
            )
            for version in new_versions:
                latest_revision_qs = latest_revision_qs.filter(
                    version__object_id=version.object_id,
                    version__content_type_id=version.content_type_id,
                )
            latest_revision = latest_revision_qs.order_by("-pk").first()
            # If we have a latest revision, compare it to the current revision.
            if latest_revision is not None:
                previous_versions = latest_revision.version_set.all()

                # Creates a sorted list of version dicts for comparison.
                def get_version_dicts(versions):
                    return [
                        version.local_field_dict
                        for version
                        in sorted(versions, key=lambda v: (v.content_type_id, v.object_id))
                    ]
                save_revision = get_version_dicts(previous_versions) != get_version_dicts(new_versions)
        # Only save if we're always saving, or have changes.
        if save_revision:
            # Save a new revision.
            revision = Revision(
                manager_slug=revision_manager._manager_slug,
                user=user,
                comment=comment,
            )
            # Send the pre_revision_commit signal.
            pre_revision_commit.send(
                sender=revision_manager,
                instances=objects,
                revision=revision,
                versions=new_versions,
            )
            # Save the revision.
            with transaction.atomic(using=self.db):
                revision.save(using=self.db)
                # Save version models.
                for version in new_versions:
                    version.revision = revision
                    version.save(using=self.db)
                # Save the meta information.
                for meta_obj in meta:
                    meta_obj.revision = revision
                    meta_obj.save(using=self.db)
            # Send the post_revision_commit signal.
            post_revision_commit.send(
                sender=revision_manager,
                instances=objects,
                revision=revision,
                versions=new_versions,
            )
            # Return the revision.
            return revision


@python_2_unicode_compatible
class Revision(models.Model):

    """A group of related object versions."""

    objects = RevisionModelManager.from_queryset(RevisionQuerySet)()

    manager_slug = models.CharField(
        max_length=191,
        db_index=True,
        default="default",
    )

    date_created = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("date created"),
        help_text="The date and time this revision was created.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("user"),
        help_text="The user who created this revision.",
    )

    comment = models.TextField(
        blank=True,
        verbose_name=_("comment"),
        help_text="A text comment on this revision.",
    )

    def revert(self, delete=False):
        """Reverts all objects in this revision."""
        # Group the models by the database of the serialized model.
        versions_by_db = defaultdict(list)
        for version in self.version_set.iterator():
            versions_by_db[version.db].append(version)
        # For each db, perform a separate atomic revert.
        for version_db, versions in versions_by_db.items():
            with transaction.atomic(using=version_db):
                # Optionally delete objects no longer in the current revision.
                if delete:
                    # Get a set of all objects in this revision.
                    old_revision = set()
                    for version in versions:
                        # Load the content type from the same DB as the Version, since it logically has to be in the
                        # same DB for the foreign key to work.
                        content_type = ContentType.objects.db_manager(
                            using=version._state.db,
                        ).get_for_id(version.content_type_id)
                        model_cls = content_type.model_class()
                        try:
                            # Load the model instance from the same DB as it was saved under.
                            old_revision.add(model_cls._base_manager.using(version.db).get(pk=version.object_id))
                        except model_cls.DoesNotExist:
                            pass
                    # Calculate the set of all objects that are in the revision now.
                    revision_manager = RevisionManager.get_manager(self.manager_slug)
                    current_revision = chain.from_iterable(
                        revision_manager._follow_relationships(obj)
                        for obj in old_revision
                    )
                    # Delete objects that are no longer in the current revision.
                    for item in current_revision:
                        if item not in old_revision:
                            item.delete()
                # Attempt to revert all revisions.
                safe_revert(versions)

    def __str__(self):
        return ", ".join(force_text(version) for version in self.version_set.all())

    class Meta:
        app_label = "reversion"


def _post_revision_context_end_receiver(sender, objects, serialized_objects, ignore_duplicates, user, comment,
                                        meta, db, **kwargs):
    Revision.objects.db_manager(db).save_revision(
        objects=objects,
        serialized_objects=serialized_objects,
        ignore_duplicates=ignore_duplicates,
        user=user,
        comment=comment,
        meta=meta,
        revision_manager=sender,
    )
post_revision_context_end.connect(_post_revision_context_end_receiver)


class VersionQuerySet(models.QuerySet):

    def for_revision_manager(self, revision_manager):
        """
        Returns all versions created using the given revision manager.
        """
        return self.filter(revision__manager_slug=revision_manager._manager_slug)

    def get_unique(self):
        """
        Returns a generator of unique version data.
        """
        last_field_dict = None
        for version in self.iterator():
            if last_field_dict != version.local_field_dict:
                yield version
            last_field_dict = version.local_field_dict


@python_2_unicode_compatible
class Version(models.Model):

    """A saved version of a database model."""

    objects = VersionQuerySet.as_manager()

    revision = models.ForeignKey(
        Revision,
        on_delete=models.CASCADE,
        help_text="The revision that contains this version.",
    )

    object_id = models.CharField(
        max_length=191,
        help_text="Primary key of the model under version control.",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Content type of the model under version control.",
    )

    # A link to the current instance, not the version stored in this Version!
    object = GenericForeignKey(
        ct_field="content_type",
        fk_field="object_id",
    )

    db = models.CharField(
        max_length=191,
        help_text="The database the model under version control is stored in.",
    )

    format = models.CharField(
        max_length=255,
        help_text="The serialization format used by this model.",
    )

    serialized_data = models.TextField(
        help_text="The serialized form of this version of the model.",
    )

    object_repr = models.TextField(
        help_text="A string representation of the object.",
    )

    @cached_property
    def object_version(self):
        """The stored version of the model."""
        data = self.serialized_data
        data = force_text(data.encode("utf8"))
        return list(serializers.deserialize(self.format, data, ignorenonexistent=True))[0]

    @cached_property
    def local_field_dict(self):
        """
        A dictionary mapping field names to field values in this version
        of the model.

        Parent links of inherited multi-table models will not be followed.
        """
        object_version = self.object_version
        obj = object_version.object
        result = {}
        for field in obj._meta.fields:
            result[field.name] = field.value_from_object(obj)
        result.update(object_version.m2m_data)
        return result

    @cached_property
    def field_dict(self):
        """
        A dictionary mapping field names to field values in this version
        of the model.

        This method will follow parent links, if present.
        """
        object_version = self.object_version
        obj = object_version.object
        result = self.local_field_dict
        # Add parent data.
        for parent_class, field in obj._meta.concrete_model._meta.parents.items():
            field = field or obj.pk
            if obj._meta.proxy and parent_class == obj._meta.concrete_model:
                continue
            content_type = ContentType.objects.get_for_model(parent_class)
            parent_id = getattr(obj, field.attname)
            parent_version = Version.objects.get(
                revision__id=self.revision_id,
                content_type=content_type,
                object_id=parent_id,
            )
            result.update(parent_version.field_dict)
        return result

    def revert(self):
        """Recovers the model in this version."""
        self.object_version.save(using=self.db)

    def __str__(self):
        """Returns a unicode representation."""
        return self.object_repr

    class Meta:
        app_label = 'reversion'
        unique_together = (
            ("object_id", "content_type", "revision"),
        )


class Str(models.Func):

    """Casts a value to the database's text type."""

    function = "CAST"
    template = "%(function)s(%(expressions)s as %(db_type)s)"

    def __init__(self, expression):
        super(Str, self).__init__(expression, output_field=models.TextField())

    def as_sql(self, compiler, connection):
        self.extra["db_type"] = self.output_field.db_type(connection)
        return super(Str, self).as_sql(compiler, connection)


@models.Field.register_lookup
class ReversionSubqueryLookup(models.Lookup):

    """
    Performs a subquery using an SQL `IN` clause, selecting the bast strategy
    for the database.
    """

    lookup_name = "reversion_in"

    # Strategies.

    def __init__(self, lhs, rhs):
        rhs, self.rhs_field_name = rhs
        rhs = rhs.values_list(self.rhs_field_name, flat=True)
        super(ReversionSubqueryLookup, self).__init__(lhs, rhs)
        # Introspect the lhs and rhs, so we can fail early if it's unexpected.
        self.lhs_field = self.lhs.output_field
        self.rhs_field = self.rhs.model._meta.get_field(self.rhs_field_name)

    def _as_in_memory_sql(self, compiler, connection):
        """
        The most reliable strategy. The subquery is performed as two separate queries,
        buffering the subquery in application memory.

        This will work in all databases, but can use a lot of memory.
        """
        return compiler.compile(In(self.lhs, list(self.rhs.iterator())))

    def _as_in_database_sql(self, compiler, connection):
        """
        Theoretically the best strategy. The subquery is performed as a single database
        query, using nested SELECT.

        This will only work if the `Str` function supports the database.
        """
        lhs = self.lhs
        rhs = self.rhs
        # If fields are not the same internal type, we have to cast both to string.
        if self.lhs_field.get_internal_type() != self.rhs_field.get_internal_type():
            # If the left hand side is not a text field, we need to cast it.
            if not isinstance(self.lhs_field, (models.CharField, models.TextField)):
                lhs = Str(lhs)
            # If the right hand side is not a text field, we need to cast it.
            if not isinstance(self.rhs_field, (models.CharField, models.TextField)):
                rhs_str_name = "%s_str" % self.rhs_field.name
                rhs = rhs.annotate(**{
                    rhs_str_name: Str(self.rhs_field.name),
                }).values_list(rhs_str_name, flat=True)
        # All done!
        return compiler.compile(In(lhs, rhs))

    def as_sql(self, compiler, connection):
        """The fallback strategy for all databases is a safe in-memory subquery."""
        return self._as_in_memory_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        """SQLite supports the `Str` function, so can use the efficient in-database subquery."""
        return self._as_in_database_sql(compiler, connection)

    def as_mysql(self, compiler, connection):
        """MySQL can choke on complex subqueries, so uses the safe in-memory subquery."""
        # TODO: Add a version selector to use the in-database subquery if a safe version is known.
        return self._as_in_memory_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        """Postgres supports the `Str` function, so can use the efficient in-database subquery."""
        return self._as_in_database_sql(compiler, connection)
