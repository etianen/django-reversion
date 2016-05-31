"""Revision management for django-reversion."""

from __future__ import unicode_literals
import warnings
from functools import wraps, partial
from threading import local
from weakref import WeakValueDictionary
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.signals import request_finished
from django.db import models
from django.db.models import Max
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.utils.encoding import force_text
from reversion.compat import remote_field
from reversion.errors import RevisionManagementError, RegistrationError
from reversion.signals import post_revision_context_end


class VersionAdapter(object):

    """Adapter class for serializing a registered model."""

    # Fields to include in the serialized data.
    fields = None

    # Fields to exclude from the serialized data.
    exclude = ()

    # Foreign key relationships to follow when saving a version of this model.
    follow = ()

    # The serialization format to use.
    format = "json"

    # Signals to listen to.
    signals = (post_save,)

    # Eager signals to listen to.
    eager_signals = ()

    # Whether to save content types for the concrete model of any proxy models.
    for_concrete_model = True

    def __init__(self, model):
        self.model = model

    def get_all_signals(self):
        return tuple(self.signals) + tuple(self.eager_signals)

    def get_fields_to_serialize(self):
        """Returns an iterable of field names to serialize in the version data."""
        opts = self.model._meta.concrete_model._meta
        fields = self.fields or (field.name for field in opts.local_fields + opts.local_many_to_many)
        fields = (opts.get_field(field) for field in fields if field not in self.exclude)
        for field in fields:
            if remote_field(field):
                yield field.name
            else:
                yield field.attname

    def get_followed_relations(self, obj):
        """Returns an iterable of related models that should be included in the revision data."""
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
            except ObjectDoesNotExist:  # pragma: no cover
                continue
            if isinstance(related, models.Model):
                yield related
            elif isinstance(related, (models.Manager, QuerySet)):
                for related_obj in related.all():
                    yield related_obj
            elif related is not None:  # pragma: no cover
                raise TypeError((
                    "Cannot follow the relationship {relationship}. "
                    "Expected a model or QuerySet, found {related}"
                ).format(
                    relationship=relationship,
                    related=related,
                ))

    def get_serialization_format(self):
        """Returns the serialization format to use."""
        return self.format

    def get_serialized_data(self, obj):
        """Returns a string of serialized data for the given obj."""
        return serializers.serialize(
            self.get_serialization_format(),
            (obj,),
            fields=list(self.get_fields_to_serialize()),
        )

    def get_object_id(self, obj):
        """
        Returns the object id to save for the given object.
        """
        return force_text(obj.pk)

    def get_content_type(self, obj, db):
        """Returns the content type to use for the given object."""
        return ContentType.objects.db_manager(db).get_for_model(obj, for_concrete_model=self.for_concrete_model)

    def get_version_data(self, obj, db):
        """Creates the version data to be saved to the version model."""
        return {
            "object_id": self.get_object_id(obj),
            "content_type": self.get_content_type(obj, db),
            "format": self.get_serialization_format(),
            "serialized_data": self.get_serialized_data(obj),
            "object_repr": force_text(obj),
        }


class RevisionContextStackFrame(object):

    def __init__(self, is_managing_manually, is_invalid=False, ignore_duplicates=False):
        self.is_managing_manually = is_managing_manually
        self.is_invalid = is_invalid
        self.ignore_duplicates = ignore_duplicates
        self.objects = defaultdict(dict)
        self.meta = []

    def fork(self, is_managing_manually):
        return RevisionContextStackFrame(is_managing_manually, self.is_invalid, self.ignore_duplicates)

    def join(self, other_context):
        if not other_context.is_invalid:
            for manager_name, object_versions in other_context.objects.items():
                self.objects[manager_name].update(object_versions)
            self.meta.extend(other_context.meta)


def get_version_data_key(version_data):
    return (version_data["content_type"], version_data["object_id"])


class RevisionContextManager(local):

    """Manages the state of the current revision."""

    def __init__(self):
        self.clear()
        request_finished.connect(self._request_finished_receiver)

    def clear(self):
        """Puts the revision manager back into its default state."""
        self._user = None
        self._comment = ""
        self._stack = []
        self._db = None

    def is_active(self):
        """Returns whether there is an active revision for this thread."""
        return bool(self._stack)

    def _assert_active(self):
        """Checks for an active revision, throwning an exception if none."""
        if not self.is_active():
            raise RevisionManagementError("There is no active revision for this thread")

    @property
    def _current_frame(self):
        self._assert_active()
        return self._stack[-1]

    def start(self, manage_manually=False):
        """
        Begins a revision for this thread.

        This MUST be balanced by a call to `end`.  It is recommended that you
        leave these methods alone and instead use the `create_revision`
        decorator/context manager.
        """
        if self.is_active():
            self._stack.append(self._current_frame.fork(manage_manually))
        else:
            self._stack.append(RevisionContextStackFrame(manage_manually))

    def end(self):
        """Ends a revision for this thread."""
        self._assert_active()
        stack_frame = self._stack.pop()
        if self._stack:
            self._current_frame.join(stack_frame)
        else:
            try:
                if not stack_frame.is_invalid:
                    for manager, manager_objects in stack_frame.objects.items():
                        post_revision_context_end.send(
                            sender=manager,
                            objects=[obj for obj in manager_objects.values() if not isinstance(obj, dict)],
                            serialized_objects=[obj for obj in manager_objects.values() if isinstance(obj, dict)],
                            user=self._user,
                            comment=self._comment,
                            meta=stack_frame.meta,
                            ignore_duplicates=stack_frame.ignore_duplicates,
                            db=self._db,
                        )
            finally:
                self.clear()

    # Revision context properties that apply to the entire stack.

    def get_db(self):
        """Returns the current DB alias being used."""
        return self._db

    def set_db(self, db):
        """Sets the DB alias to use."""
        self._db = db

    def set_user(self, user):
        """Sets the current user for the revision."""
        self._assert_active()
        self._user = user

    def get_user(self):
        """Gets the current user for the revision."""
        self._assert_active()
        return self._user

    def set_comment(self, comment):
        """Sets the comments for the revision."""
        self._assert_active()
        self._comment = comment

    def get_comment(self):
        """Gets the current comment for the revision."""
        self._assert_active()
        return self._comment

    # Revision context properties that apply to the current stack frame.

    def is_managing_manually(self):
        """Returns whether this revision context has manual management enabled."""
        return self._current_frame.is_managing_manually

    def invalidate(self):
        """Marks this revision as broken, so should not be commited."""
        self._current_frame.is_invalid = True

    def is_invalid(self):
        """Checks whether this revision is invalid."""
        return self._current_frame.is_invalid

    def add_to_context(self, revision_manager, obj):
        """
        Adds an object to the current revision.
        """
        adapter = revision_manager.get_adapter(obj.__class__)
        self._current_frame.objects[revision_manager][(
            adapter.get_content_type(obj, self._db),
            adapter.get_object_id(obj),
        )] = obj

    def add_to_context_serialized(self, revision_manager, version_data):
        """
        Adds a dict of pre-serialized version data to the current revision
        """
        self._current_frame.objects[revision_manager][get_version_data_key(version_data)] = version_data

    def add_meta(self, cls, **kwargs):
        """Adds a class of meta information to the current revision."""
        self._current_frame.meta.append((cls(**kwargs)))

    def set_ignore_duplicates(self, ignore_duplicates):
        """Sets whether to ignore duplicate revisions."""
        self._current_frame.ignore_duplicates = ignore_duplicates

    def get_ignore_duplicates(self):
        """Gets whether to ignore duplicate revisions."""
        return self._current_frame.ignore_duplicates

    # Signal receivers.

    def _request_finished_receiver(self, **kwargs):
        """
        Called at the end of a request, ensuring that any open revisions
        are closed. Not closing all active revisions can cause memory leaks
        and weird behaviour.
        """
        while self.is_active():  # pragma: no cover
            warnings.warn("Active revision context open at the end of a request.")
            self.end()

    # High-level context management.

    def create_revision(self, manage_manually=False):
        """
        Marks up a block of code as requiring a revision to be created.

        The returned context manager can also be used as a decorator.
        """
        return RevisionContext(self, manage_manually)


class RevisionContext(object):

    """An individual context for a revision."""

    def __init__(self, context_manager, manage_manually):
        """Initializes the revision context."""
        self._context_manager = context_manager
        self._manage_manually = manage_manually

    def __enter__(self):
        """Enters a block of revision management."""
        self._context_manager.start(self._manage_manually)

    def __exit__(self, exc_type, exc_value, traceback):
        """Leaves a block of revision management."""
        try:
            if exc_type is not None:
                self._context_manager.invalidate()
        finally:
            self._context_manager.end()

    def __call__(self, func):
        """Allows this revision context to be used as a decorator."""
        @wraps(func)
        def do_revision_context(*args, **kwargs):
            with self:
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
        raise RegistrationError("No revision manager exists with the slug %r" % manager_slug)  # pragma: no cover

    def __init__(self, manager_slug, revision_context_manager=revision_context_manager):
        """Initializes the revision manager."""
        # Check the slug is unique for this revision manager.
        if manager_slug in RevisionManager._created_managers:  # pragma: no cover
            raise RegistrationError("A revision manager has already been created with the slug %r" % manager_slug)
        # Store a reference to this manager.
        self.__class__._created_managers[manager_slug] = self
        # Store config params.
        self._manager_slug = manager_slug
        self._registered_models = {}
        self._revision_context_manager = revision_context_manager
        # Proxies to common context methods.
        self._revision_context = revision_context_manager.create_revision()

    # Registration methods.

    def is_registered(self, model):
        """
        Checks whether the given model has been registered with this revision
        manager.
        """
        return model in self._registered_models

    def get_registered_models(self):
        """Returns an iterable of all registered models."""
        return list(self._registered_models.keys())

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
        if field_overrides:
            adapter_cls = type(adapter_cls.__name__, (adapter_cls,), field_overrides)
        # Perform the registration.
        adapter_obj = adapter_cls(model)
        self._registered_models[model] = adapter_obj
        # Connect to the selected signals of the model.
        for signal in adapter_obj.get_all_signals():
            signal.connect(self._signal_receiver, model)
        return model

    def get_adapter(self, model):
        """Returns the registration information for the given model class."""
        if self.is_registered(model):
            return self._registered_models[model]
        raise RegistrationError("{model} has not been registered with django-reversion".format(
            model=model,
        ))

    def unregister(self, model):
        """Removes a model from version control."""
        if not self.is_registered(model):
            raise RegistrationError("{model} has not been registered with django-reversion".format(
                model=model,
            ))
        adapter_obj = self._registered_models.pop(model)
        # Connect to the selected signals of the model.
        for signal in adapter_obj.get_all_signals():
            signal.disconnect(self._signal_receiver, model)

    def _get_versions(self, db=None):
        """Returns all versions that apply to this manager."""
        from reversion.models import Version
        return Version.objects.using(db).for_revision_manager(self)

    # Revision management API.

    def get_for_object_reference(self, model, object_id, db=None):
        """
        Returns all versions for the given object reference.

        The results are returned with the most recent versions first.
        """
        content_type = ContentType.objects.db_manager(db).get_for_model(model)
        versions = self._get_versions(db).filter(
            content_type=content_type,
            object_id=object_id,
        ).select_related("revision").order_by("-pk")
        return versions

    def get_for_object(self, obj, db=None):
        """
        Returns all the versions of the given object, ordered by date created.

        The results are returned with the most recent versions first.
        """
        return self.get_for_object_reference(obj.__class__, obj.pk, db)

    def get_unique_for_object(self, obj, db=None):
        """
        Returns unique versions associated with the object.

        The results are returned with the most recent versions first.
        """
        warnings.warn(
            "Use get_for_object().get_unique() instead of get_unique_for_object().",
            PendingDeprecationWarning)
        return list(self.get_for_object(obj, db).get_unique())

    def get_for_date(self, object, date, db=None):
        """Returns the latest version of an object for the given date."""
        return (self.get_for_object(object, db)
                .filter(revision__date_created__lte=date)[:1]
                .get())

    def get_deleted(self, model_class, db=None, model_db=None):
        """
        Returns all the deleted versions for the given model class.

        The results are returned with the most recent versions first.
        """
        model_db = model_db or db
        content_type = ContentType.objects.db_manager(db).get_for_model(model_class)
        # Return the deleted versions!
        return self._get_versions(db).filter(
            pk__reversion_in=(self._get_versions(db).filter(
                content_type=content_type,
            ).exclude(
                object_id__reversion_in=(model_class._base_manager.using(model_db), model_class._meta.pk.name),
            ).values_list("object_id").annotate(
                id=Max("id"),
            ), "id")
        ).order_by("-id")

    # Serialization.

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

    def _get_version_data_list(self, instance, db):
        return [
            self.get_adapter(obj.__class__).get_version_data(obj, db)
            for obj
            in self._follow_relationships(instance)
        ]

    # Signal receivers.

    def _signal_receiver(self, instance, signal, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            adapter = self.get_adapter(instance.__class__)
            if signal in adapter.eager_signals:
                for version_data in self._get_version_data_list(instance, self._revision_context_manager._db):
                    self._revision_context_manager.add_to_context_serialized(self, version_data)
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


# Context management.
create_revision = revision_context_manager.create_revision


# Revision meta data.
get_db = revision_context_manager.get_db
set_db = revision_context_manager.set_db
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
