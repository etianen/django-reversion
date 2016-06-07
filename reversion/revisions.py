"""Revision management for django-reversion."""

from __future__ import unicode_literals
import warnings
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps, partial
from itertools import chain
from threading import local
from weakref import WeakValueDictionary
from django.apps import apps
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, router
from django.db.models import Max
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.utils.encoding import force_text
from django.utils import timezone
from reversion.compat import remote_field
from reversion.errors import RevisionManagementError, RegistrationError
from reversion.signals import pre_revision_commit, post_revision_commit


class VersionAdapter(object):

    """
    Adapter class for serializing a registered model.
    """

    def __init__(self, model):
        self.model = model

    fields = None
    """
    Field named to include in the serialized data.

    Set to `None` to include all model fields.
    """

    exclude = ()
    """
    Field names to exclude from the serialized data.
    """

    def get_fields_to_serialize(self):
        """
        Returns an iterable of field names to serialize in the version data.
        """
        opts = self.model._meta.concrete_model._meta
        fields = (
            field.name
            for field
            in opts.local_fields + opts.local_many_to_many
        ) if self.fields is None else self.fields
        fields = (opts.get_field(field) for field in fields if field not in self.exclude)
        for field in fields:
            if remote_field(field):
                yield field.name
            else:
                yield field.attname

    follow = ()
    """
    Foreign-key relationships to follow when saving a version of this model.

    `ForeignKey`, `ManyToManyField` and reversion `ForeignKey` relationships
    are supported. Any property that returns a `Model` or `QuerySet`
    is also supported.
    """

    def get_followed_relations(self, obj):
        """
        Returns an iterable of related models that should be included in the revision data.

        `obj` - A model instance.
        """
        for relationship in self.follow:
            # Clear foreign key cache.
            try:
                related_field = obj._meta.get_field(relationship)
            except models.FieldDoesNotExist:
                pass
            else:
                if isinstance(related_field, models.ForeignKey):
                    if hasattr(obj, related_field.get_cache_name()):
                        delattr(obj, related_field.get_cache_name())
            # Get the referenced obj(s).
            try:
                related = getattr(obj, relationship)
            except ObjectDoesNotExist:
                continue
            if isinstance(related, models.Model):
                yield related
            elif isinstance(related, (models.Manager, QuerySet)):
                for related_obj in related.all():
                    yield related_obj
            elif related is not None:
                raise TypeError((
                    "Cannot follow the relationship {relationship}. "
                    "Expected a model or QuerySet, found {related}"
                ).format(
                    relationship=relationship,
                    related=related,
                ))

    format = "json"
    """
    The name of a Django serialization format to use when saving the version.
    """

    def get_serialization_format(self):
        """
        Returns the name of a Django serialization format to use when saving the version.
        """
        return self.format

    for_concrete_model = True
    """
    If `True` (default), then proxy models will be saved under the same content
    type as their concrete model. If `False`, then proxy models will be saved
    under their own content type, effectively giving proxy models their own
    distinct history.
    """

    signals = (post_save,)
    """
    Django signals that trigger saving a version.

    The model version will be saved at the end of the outermost revision block.
    """

    eager_signals = ()
    """
    Django signals that trigger saving a version.

    The model version will be saved immediately, making it suitable for signals
    that trigger before a model is deleted.
    """

    def get_all_signals(self):
        """
        Returns an iterable of all signals that trigger saving a version.
        """
        return chain(self.signals, self.eager_signals)

    def get_serialized_data(self, obj):
        """
        Returns a string of serialized data for the given model instance.

        `obj` - A model instance.
        """
        return serializers.serialize(
            self.get_serialization_format(),
            (obj,),
            fields=list(self.get_fields_to_serialize()),
        )

    def get_content_type_natural_key(self, model):
        """
        Returns a tuple of (app_label, model_name) for the given model.
        """
        if self.for_concrete_model:
            opts = model._meta.concrete_model._meta
        else:
            opts = model._meta
        return (opts.app_label, opts.model_name)

    def get_version_data(self, obj):
        """
        Creates a dict of version data to be saved to the version model.

        `obj` - A model instance.
        """
        return {
            "content_type": self.get_content_type_natural_key(obj.__class__),
            "object_id": force_text(obj.pk),
            "db": obj._state.db,
            "format": self.get_serialization_format(),
            "serialized_data": self.get_serialized_data(obj),
            "object_repr": force_text(obj),
        }

    def revert(self, version):
        """
        Reverts the given version to the database.
        """
        version.object_version.save(using=version.db)


class RevisionMeta(object):

    """Custom metadata assigned to a revision."""

    def __init__(self, model, **values):
        self.model = model
        self.values = values

    def save(self, revision, db):
        return self.model._default_manager.db_manager(db).create(revision=revision, **self.values)


class RevisionContextStackFrame(object):

    def __init__(self, manage_manually, db, user, comment, ignore_duplicates, manager_objects, meta):
        # Block-scoped properties.
        self.manage_manually = manage_manually
        self.db = db
        # Revision-scoped properties.
        self.user = user
        self.comment = comment
        self.ignore_duplicates = ignore_duplicates
        self.manager_objects = manager_objects
        self.meta = meta

    def fork(self, manage_manually, db):
        return RevisionContextStackFrame(
            manage_manually,
            db,
            self.user,
            self.comment,
            self.ignore_duplicates,
            defaultdict(dict, {
                manager: objects.copy()
                for manager, objects
                in self.manager_objects.items()
            }),
            self.meta[:],
        )

    def join(self, other_frame):
        self.user = other_frame.user
        self.comment = other_frame.comment
        self.ignore_duplicates = other_frame.ignore_duplicates
        self.manager_objects = other_frame.manager_objects
        self.meta = other_frame.meta


class RevisionContextManager(local):

    def __init__(self):
        self._stack = []

    def is_active(self):
        """
        Returns whether there is an active revision for this thread.
        """
        return bool(self._stack)

    @property
    def _current_frame(self):
        if not self.is_active():
            raise RevisionManagementError("There is no active revision for this thread")
        return self._stack[-1]

    # Block-scoped properties.

    def is_managing_manually(self):
        """Returns whether this revision context has manual management enabled."""
        return self._current_frame.manage_manually

    # Revision-scoped properties.

    def set_user(self, user):
        """Sets the current user for the revision."""
        self._current_frame.user = user

    def get_user(self):
        """Gets the current user for the revision."""
        return self._current_frame.user

    def set_comment(self, comment):
        """Sets the comments for the revision."""
        self._current_frame.comment = comment

    def get_comment(self):
        """Gets the current comment for the revision."""
        return self._current_frame.comment

    def set_ignore_duplicates(self, ignore_duplicates):
        """Sets whether to ignore duplicate revisions."""
        self._current_frame.ignore_duplicates = ignore_duplicates

    def get_ignore_duplicates(self):
        """Gets whether to ignore duplicate revisions."""
        return self._current_frame.ignore_duplicates

    def _get_version_id(self, revision_manager, obj):
        adapter = revision_manager.get_adapter(obj.__class__)
        return (adapter.get_content_type_natural_key(obj.__class__), force_text(obj.pk))

    def add_to_context(self, revision_manager, obj):
        """
        Adds an object to the current revision.
        """
        self._current_frame.manager_objects[revision_manager][self._get_version_id(revision_manager, obj)] = obj

    def add_to_context_eager(self, revision_manager, obj):
        """
        Adds a dict of pre-serialized version data to the current revision
        """
        for relation in revision_manager._follow_relationships(obj):
            adapter = revision_manager.get_adapter(relation.__class__)
            version_data = adapter.get_version_data(relation)
            self._current_frame.manager_objects[revision_manager][self._get_version_id(
                revision_manager,
                relation,
            )] = version_data

    def add_meta(self, model, **values):
        """Adds a model of meta information to the current revision."""
        self._current_frame.meta.append(RevisionMeta(model, **values))

    # High-level context management.

    @contextmanager
    def _create_revision_context(self, manage_manually, db):
        # Create a new stack frame.
        if self.is_active():
            stack_frame = self._current_frame.fork(manage_manually, db)
        else:
            stack_frame = RevisionContextStackFrame(
                manage_manually=manage_manually,
                db=db,
                user=None,
                comment="",
                ignore_duplicates=False,
                manager_objects=defaultdict(dict),
                meta=[],
            )
        # Run the revision context in a transaction.
        with transaction.atomic(using=db):
            self._stack.append(stack_frame)
            try:
                yield
            finally:
                self._stack.pop()
            # Only save for a db if that's the last stack frame for that db.
            if not any(frame.db == stack_frame.db for frame in self._stack):
                for manager, objects in stack_frame.manager_objects.items():
                    manager.save_revision(
                        objects=list(objects.values()),
                        user=stack_frame.user,
                        comment=stack_frame.comment,
                        meta=stack_frame.meta,
                        ignore_duplicates=stack_frame.ignore_duplicates,
                        db=db,
                    )
            # Join the stack frame on success.
            if self._stack:
                self._current_frame.join(stack_frame)

    def create_revision(self, manage_manually=False, db=None):
        """
        Marks up a block of code as requiring a revision to be created.

        The returned context manager can also be used as a decorator.
        """
        from reversion.models import Revision
        db = router.db_for_write(Revision) if db is None else db
        return ContextWrapper(self._create_revision_context, (manage_manually, db))


class ContextWrapper(object):

    def __init__(self, func, args):
        self._func = func
        self._args = args
        self._context = func(*args)

    def __enter__(self):
        return self._context.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self._context.__exit__(exc_type, exc_value, traceback)

    def __call__(self, func):
        @wraps(func)
        def do_revision_context(*args, **kwargs):
            with self._func(*self._args):
                return func(*args, **kwargs)
        return do_revision_context


# A shared, thread-safe context manager.
revision_context_manager = RevisionContextManager()


class RevisionManager(object):

    """Manages the configuration and creation of revisions."""

    _created_managers = WeakValueDictionary()

    @classmethod
    def get_created_managers(cls):
        """Returns all created revision managers."""
        return list(cls._created_managers.items())

    @classmethod
    def get_manager(cls, manager_slug):
        """Returns the manager with the given slug."""
        if manager_slug in cls._created_managers:
            return cls._created_managers[manager_slug]
        raise RegistrationError("No revision manager exists with the slug %r" % manager_slug)

    def __init__(self, manager_slug, revision_context_manager=revision_context_manager):
        """Initializes the revision manager."""
        # Check the slug is unique for this revision manager.
        if manager_slug in RevisionManager._created_managers:
            raise RegistrationError("A revision manager has already been created with the slug %r" % manager_slug)
        # Store a reference to this manager.
        self.__class__._created_managers[manager_slug] = self
        # Store config params.
        self._manager_slug = manager_slug
        self._registered_models = {}
        self._revision_context_manager = revision_context_manager

    # Registration methods.

    def _get_registration_key(self, model):
        return (model._meta.app_label, model._meta.model_name)

    def is_registered(self, model):
        """
        Checks whether the given model has been registered with this revision
        manager.
        """
        return self._get_registration_key(model) in self._registered_models

    def get_registered_models(self):
        """Returns an iterable of all registered models."""
        return (apps.get_model(*key) for key in self._registered_models.keys())

    def register(self, model=None, adapter_cls=VersionAdapter, **field_overrides):
        """Registers a model with this revision manager."""
        # Return a class decorator if model is not given
        if model is None:
            return partial(self.register, adapter_cls=adapter_cls, **field_overrides)
        # Prevent multiple registration.
        if self.is_registered(model):
            raise RegistrationError("{model} has already been registered with django-reversion".format(
                model=model,
            ))
        # Perform any customization.
        adapter_cls = type(adapter_cls.__name__, (adapter_cls,), field_overrides)
        # Perform the registration.
        adapter_obj = adapter_cls(model)
        self._registered_models[self._get_registration_key(model)] = adapter_obj
        # Connect to the selected signals of the model.
        for signal in adapter_obj.get_all_signals():
            signal.connect(self._signal_receiver, model)
        return model

    def get_adapter(self, model):
        """Returns the registration information for the given model class."""
        if self.is_registered(model):
            return self._registered_models[self._get_registration_key(model)]
        raise RegistrationError("{model} has not been registered with django-reversion".format(
            model=model,
        ))

    def unregister(self, model):
        """Removes a model from version control."""
        if not self.is_registered(model):
            raise RegistrationError("{model} has not been registered with django-reversion".format(
                model=model,
            ))
        adapter_obj = self._registered_models.pop(self._get_registration_key(model))
        # Connect to the selected signals of the model.
        for signal in adapter_obj.get_all_signals():
            signal.disconnect(self._signal_receiver, model)

    def _get_content_type(self, model, db):
        from django.contrib.contenttypes.models import ContentType
        adapter = self.get_adapter(model)
        return ContentType.objects.db_manager(db).get_by_natural_key(*adapter.get_content_type_natural_key(model))

    def _get_versions(self, model, db, model_db):
        from reversion.models import Version
        model_db = router.db_for_write(model) if model_db is None else model_db
        return Version.objects.using(db).filter(
            revision__manager_slug=self._manager_slug,
            content_type=self._get_content_type(model, db),
            db=model_db,
        )

    # Revision management API.

    def get_for_object_reference(self, model, object_id, db=None, model_db=None):
        """
        Returns all versions for the given object reference.

        The results are returned with the most recent versions first.
        """
        return self._get_versions(model, db, model_db).filter(
            object_id=object_id,
        ).order_by("-pk")

    def get_for_object(self, obj, db=None, model_db=None):
        """
        Returns all the versions of the given object, ordered by date created.

        The results are returned with the most recent versions first.
        """
        return self.get_for_object_reference(obj.__class__, obj.pk, db=db, model_db=model_db)

    def get_unique_for_object(self, obj, db=None, model_db=None):
        """
        Returns unique versions associated with the object.

        The results are returned with the most recent versions first.
        """
        warnings.warn(
            (
                "Use get_for_object().get_unique() instead of get_unique_for_object(). "
                "get_unique_for_object() will be removed in django-reversion 1.12.0"
            ),
            DeprecationWarning
        )
        return list(self.get_for_object(obj, db=db, model_db=model_db).get_unique())

    def get_for_date(self, obj, date, db=None, model_db=None):
        """Returns the latest version of an object for the given date."""
        warnings.warn(
            (
                "Use get_for_object().filter(revision__date_created__lte=date)[:1].get() instead "
                "of get_for_date(). get_for_date() will be removed in django-reversion 1.12.0"
            ),
            DeprecationWarning
        )
        return self.get_for_object(obj, db=db, model_db=model_db).filter(revision__date_created__lte=date)[:1].get()

    def get_deleted(self, model, db=None, model_db=None):
        """
        Returns all the deleted versions for the given model class.

        The results are returned with the most recent versions first.
        """
        return self._get_versions(model, db, model_db).filter(
            pk__reversion_in=(self._get_versions(model, db, model_db).exclude(
                object_id__reversion_in=(model._default_manager.using(model_db), model._meta.pk.name),
            ).values_list("object_id").annotate(
                id=Max("id"),
            ), "id")
        ).order_by("-id")

    # Manual revision saving.

    def save_revision(self, objects, ignore_duplicates=False, user=None, comment="", meta=(),
                      date_created=None, db=None):
        """
        Manually saves a new revision containing the given objects.
        """
        from django.contrib.contenttypes.models import ContentType
        from reversion.models import Revision, Version
        date_created = timezone.now() if date_created is None else date_created
        # Create the object versions.
        version_data_dict = {}
        for obj in objects:
            # Handle eagerly-saved version dicts.
            if isinstance(obj, dict):
                version_data_seq = (obj,)
            # Handle model instances.
            else:
                version_data_seq = (
                    self.get_adapter(relation.__class__).get_version_data(relation)
                    for relation
                    in self._follow_relationships(obj)
                )
            # Store the version data.
            version_data_dict.update(
                ((version_data["content_type"], version_data["object_id"]), version_data)
                for version_data
                in version_data_seq
            )
        new_versions = [
            Version(
                content_type=ContentType.objects.db_manager(db).get_by_natural_key(*version_data["content_type"]),
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
            latest_revision_qs = Revision.objects.using(db).annotate(
                version_count=models.Count("version"),
            ).filter(
                version_count=len(new_versions),
                manager_slug=self._manager_slug,
            )
            for version in new_versions:
                latest_revision_qs = latest_revision_qs.filter(
                    version__object_id=version.object_id,
                    version__content_type_id=version.content_type_id,
                    version__db=version.db,
                )
            latest_revision = latest_revision_qs.order_by("-pk").first()
            # If we have a latest revision, compare it to the current revision.
            if latest_revision is not None:
                previous_versions = latest_revision.version_set.all()

                # Creates a sorted list of version keys for comparison.
                def get_version_keys(versions):
                    return [
                        (version.object_id, version.content_type_id, version.db, version.local_field_dict)
                        for version
                        in sorted(versions, key=lambda v: (v.object_id, v.content_type_id, v.db))
                    ]
                save_revision = get_version_keys(previous_versions) != get_version_keys(new_versions)
        # Only save if we're always saving, or have changes.
        if save_revision:
            # Save a new revision.
            revision = Revision(
                manager_slug=self._manager_slug,
                date_created=date_created,
                user=user,
                comment=comment,
            )
            # Send the pre_revision_commit signal.
            pre_revision_commit.send(
                sender=self,
                instances=objects,
                revision=revision,
                versions=new_versions,
            )
            # Save the revision.
            with transaction.atomic(using=db):
                revision.save(using=db)
                # Save version models.
                for version in new_versions:
                    version.revision = revision
                    version.save(using=db)
                # Save the meta information.
                for meta_obj in meta:
                    meta_obj.save(revision, db=db)
            # Send the post_revision_commit signal.
            post_revision_commit.send(
                sender=self,
                instances=objects,
                revision=revision,
                versions=new_versions,
            )
            # Return the revision.
            return revision

    # Signal receivers.

    def _follow_relationships(self, instance):
        def follow(obj):
            # If a model is created an deleted in the same revision, then it's pk will be none.
            if obj.pk is None or obj in followed_objects:
                return
            followed_objects.add(obj)
            adapter = self.get_adapter(obj.__class__)
            for related in adapter.get_followed_relations(obj):
                follow(related)
        followed_objects = set()
        follow(instance)
        return followed_objects

    def _signal_receiver(self, instance, signal, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            adapter = self.get_adapter(instance.__class__)
            if signal in adapter.eager_signals:
                self._revision_context_manager.add_to_context_eager(self, instance)
            else:
                self._revision_context_manager.add_to_context(self, instance)


# A shared revision manager.
default_revision_manager = RevisionManager("default")


# Easy registration methods.
register = default_revision_manager.register
is_registered = default_revision_manager.is_registered
unregister = default_revision_manager.unregister
get_adapter = default_revision_manager.get_adapter
get_registered_models = default_revision_manager.get_registered_models


# Manual revision saving.
save_revision = default_revision_manager.save_revision


# Context management.
create_revision = revision_context_manager.create_revision


# Revision meta data.
get_user = revision_context_manager.get_user
set_user = revision_context_manager.set_user
get_comment = revision_context_manager.get_comment
set_comment = revision_context_manager.set_comment
add_meta = revision_context_manager.add_meta
get_ignore_duplicates = revision_context_manager.get_ignore_duplicates
set_ignore_duplicates = revision_context_manager.set_ignore_duplicates


# Low level API.
get_for_object_reference = default_revision_manager.get_for_object_reference
get_for_object = default_revision_manager.get_for_object
get_unique_for_object = default_revision_manager.get_unique_for_object
get_for_date = default_revision_manager.get_for_date
get_deleted = default_revision_manager.get_deleted
