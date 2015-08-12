"""Revision management for django-reversion."""

from __future__ import unicode_literals

import warnings

from functools import wraps, partial

from threading import local

from weakref import WeakValueDictionary

import copy

from collections import defaultdict
import sys

try:
    from django.apps import apps
    get_model = apps.get_model
except ImportError:  # For Django < 1.7  pragma: no cover
    from django.db.models import get_model

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.signals import request_finished
from django.db import models, connection, transaction
from django.db.models import Max
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.utils.encoding import force_text

try:
    from django.contrib.contenttypes.fields import GenericRelation
except ImportError:  # Django < 1.9 pragma: no cover
    from django.contrib.contenttypes.generic import GenericRelation

from reversion.models import Revision, Version, has_int_pk, pre_revision_commit, post_revision_commit


class VersionTypeOperator(object):

    TYPE_OPERATOR = (
        (Version.TYPE.CREATED, Version.TYPE.CREATED, Version.TYPE.CREATED),
        (Version.TYPE.CREATED, Version.TYPE.CHANGED, Version.TYPE.CREATED),
        (Version.TYPE.CREATED, Version.TYPE.DELETED, Version.TYPE.DELETED),
        (Version.TYPE.CREATED, Version.TYPE.FOLLOW, Version.TYPE.CREATED),
        (Version.TYPE.CHANGED, Version.TYPE.CREATED, Version.TYPE.CHANGED),
        (Version.TYPE.CHANGED, Version.TYPE.CHANGED, Version.TYPE.CHANGED),
        (Version.TYPE.CHANGED, Version.TYPE.DELETED, Version.TYPE.DELETED),
        (Version.TYPE.CHANGED, Version.TYPE.FOLLOW, Version.TYPE.CHANGED),
        (Version.TYPE.DELETED, Version.TYPE.CREATED, Version.TYPE.CHANGED),
        (Version.TYPE.DELETED, Version.TYPE.CHANGED, Version.TYPE.CHANGED),
        (Version.TYPE.DELETED, Version.TYPE.DELETED, Version.TYPE.DELETED),
        (Version.TYPE.DELETED, Version.TYPE.FOLLOW, Version.TYPE.DELETED),
        (Version.TYPE.FOLLOW, Version.TYPE.CREATED, Version.TYPE.CREATED),
        (Version.TYPE.FOLLOW, Version.TYPE.CHANGED, Version.TYPE.CHANGED),
        (Version.TYPE.FOLLOW, Version.TYPE.DELETED, Version.TYPE.DELETED),
        (Version.TYPE.FOLLOW, Version.TYPE.FOLLOW, Version.TYPE.FOLLOW),
    )

    def __init__(self):
        self.operator_map = {}
        for a, b, res in self.TYPE_OPERATOR:
            self.operator_map[a] = results = self.operator_map.get(a, {})
            results[b] = res

    def __call__(self, a, b):
        return self.operator_map.get(a).get(b)


version_type_operator = VersionTypeOperator()


class VersionAdapter(object):

    """Adapter class for serializing a registered model."""

    # Fields to include in the serialized data.
    fields = ()

    # Fields to exclude from the serialized data.
    exclude = ()

    # Foreign key relationships to follow when saving a version of this model.
    follow = ()

    # The serialization format to use.
    format = 'json'

    def __init__(self, model):
        """Initializes the version adapter."""
        self.model = model

    def get_fields_to_serialize(self):
        """Returns an iterable of field names to serialize in the version data."""
        opts = self.model._meta.concrete_model._meta
        fields = self.fields or (field.name for field in opts.local_fields + opts.local_many_to_many)
        fields = (opts.get_field(field) for field in fields if not field in self.exclude)
        for field in fields:
            if field.rel:
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
                raise TypeError('Cannot follow the relationship {relationship}. Expected a model or QuerySet, found {related}'.format(
                    relationship = relationship,
                    related = related,
                ))

    def get_serialization_format(self):
        """Returns the serialization format to use."""
        return self.format

    def get_serialized_data(self, obj):
        """Returns a string of serialized data for the given obj."""
        return serializers.serialize(
            self.get_serialization_format(),
            (obj,),
            fields = list(self.get_fields_to_serialize()),
        )

    def get_version_data(self, obj, db=None):
        """Creates the version data to be saved to the version model."""
        object_id = force_text(obj.pk)
        content_type = ContentType.objects.db_manager(db).get_for_model(obj)
        if has_int_pk(obj.__class__):
            object_id_int = int(obj.pk)
        else:
            object_id_int = None
        return {
            'object_id': object_id,
            'object_id_int': object_id_int,
            'content_type': content_type,
            'format': self.get_serialization_format(),
            'serialized_data': self.get_serialized_data(obj),
            'object_repr': force_text(obj),
        }


class RevisionManagementError(Exception):

    """Exception that is thrown when something goes wrong with revision managment."""


class RevisionContextStackFrame(object):

    def __init__(self, is_managing_manually, is_invalid=False):
        self.is_managing_manually = is_managing_manually
        self.is_invalid = is_invalid
        self.objects = defaultdict(dict)
        self.meta = []

    def fork(self, is_managing_manually):
        return RevisionContextStackFrame(is_managing_manually, self.is_invalid)

    def join(self, other_context):
        if not other_context.is_invalid:
            for manager_name, object_versions in other_context.objects.items():
                self.objects[manager_name].update(object_versions)
            self.meta.extend(other_context.meta)


class RevisionContextManager(local):

    """Manages the state of the current revision."""

    def __init__(self):
        """Initializes the revision state."""
        self.clear()
        # Connect to the request finished signal.
        request_finished.connect(self._request_finished_receiver)

    def clear(self):
        """Puts the revision manager back into its default state."""
        self._user = None
        self._comment = ''
        self._stack = []
        self._callbacks = []
        self._db = None

    def is_active(self):
        """Returns whether there is an active revision for this thread."""
        return bool(self._stack)

    def _assert_active(self):
        """Checks for an active revision, throwning an exception if none."""
        if not self.is_active():  # pragma: no cover
            raise RevisionManagementError('There is no active revision for this thread')

    @property
    def _current_frame(self):
        self._assert_active()
        return self._stack[-1]

    def _prepare_data(self, type, data):
        data = callable(data) and data() or data
        data['type'] = type
        return data

    def start(self, manage_manually=False):
        """
        Begins a revision for this thread.

        This MUST be balanced by a call to `end`.  It is recommended that you
        leave these methods alone and instead use the revision context manager
        or the `create_revision` decorator.
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
                    # Save the revision data.
                    for manager, manager_context in stack_frame.objects.items():
                        revision = manager.save_revision(
                            dict(
                                (obj, self._prepare_data(type, data))
                                for obj, (type, data)
                                in manager_context.items()
                                if obj.pk is not None
                            ),
                            user = self._user,
                            comment = self._comment,
                            meta = stack_frame.meta,
                            db = self._db,
                        )
                        if revision:
                            for callback in self._callbacks:
                                callback(revision)
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

    def add_callback(self, callback):
        """Adds callback for the revision."""
        self._assert_active()
        self._callbacks.append(callback)

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

    def add_to_context(self, manager, type, obj, version_data):
        """Adds an object to the current revision."""
        manager_context = self._current_frame.objects[manager]

        if obj in manager_context:
            prev_type = manager_context[obj][0]
            type = version_type_operator(prev_type, type)

        self._current_frame.objects[manager][obj] = (type, version_data)

    def add_meta(self, cls, **kwargs):
        """Adds a class of meta information to the current revision."""
        self._current_frame.meta.append((cls, kwargs))

    # Signal receivers.

    def _request_finished_receiver(self, **kwargs):
        """
        Called at the end of a request, ensuring that any open revisions
        are closed. Not closing all active revisions can cause memory leaks
        and weird behaviour.
        """
        while self.is_active():  # pragma: no cover
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


class RegistrationError(Exception):

    """Exception thrown when registration with django-reversion goes wrong."""


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
        raise RegistrationError('No revision manager exists with the slug %r' % manager_slug)  # pragma: no cover

    def __init__(self, manager_slug, revision_context_manager=revision_context_manager):
        """Initializes the revision manager."""
        # Check the slug is unique for this revision manager.
        if manager_slug in RevisionManager._created_managers:  # pragma: no cover
            raise RegistrationError('A revision manager has already been created with the slug %r' % manager_slug)
        # Store a reference to this manager.
        self.__class__._created_managers[manager_slug] = self
        # Store config params.
        self._manager_slug = manager_slug
        self._registered_models = {}
        self._revision_context_manager = revision_context_manager
        self._eager_signals = {}
        self._signals = {}
        # Proxies to common context methods.
        self._revision_context = revision_context_manager.create_revision()

    # Registration methods.

    def _registration_key_for_model(self, model):
        meta = model._meta
        return (
            meta.app_label,
            meta.model_name,
        )

    def is_registered(self, model):
        """
        Checks whether the given model has been registered with this revision
        manager.
        """
        return self._registration_key_for_model(model) in self._registered_models

    def get_registered_models(self):
        """Returns an iterable of all registered models."""
        return [
            get_model(*key)
            for key
            in self._registered_models.keys()
        ]

    def register(self, model=None, adapter_cls=VersionAdapter, signals=None, eager_signals=None, follow_parents=True,
                 **field_overrides):
        """Registers a model with this revision manager."""
        # Default to post_save and post_delete if no signals are given
        if signals is None and eager_signals is None:
            signals = [post_save, pre_delete]
            eager_signals = [pre_delete]
        # Store signals for usage in the signal receiver
        self._eager_signals[model] = list(eager_signals or [])
        self._signals[model] = list(signals or [])
        # Return a class decorator if model is not given

        if follow_parents:
            field_overrides['follow'] = follow = field_overrides.get('follow', [])

            for parent_model, field in model._meta.parents.items():
                if field:
                    follow.append(field.name)
                if not self.is_registered(parent_model):
                    self.register(parent_model, adapter_cls, signals, eager_signals, follow_parents)

        if model is None:
            return partial(self.register, adapter_cls=adapter_cls, **field_overrides)
        # Prevent multiple registration.
        if self.is_registered(model):
            raise RegistrationError('{model} has already been registered with django-reversion'.format(
                model = model,
            ))
        # Perform any customization.
        if field_overrides:
            adapter_cls = type(adapter_cls.__name__, (adapter_cls,), field_overrides)
        # Perform the registration.
        adapter_obj = adapter_cls(model)
        self._registered_models[self._registration_key_for_model(model)] = adapter_obj
        # Connect to the selected signals of the model.
        all_signals = self._signals[model] + self._eager_signals[model]
        for signal in all_signals:
            signal.connect(self._signal_receiver, model)

        model.reversion_versions = GenericRelation(Version)
        model.reversion_versions.contribute_to_class(model, 'reversion_versions')

        return model

    def get_adapter(self, model):
        """Returns the registration information for the given model class."""
        if self.is_registered(model):
            return self._registered_models[self._registration_key_for_model(model)]
        raise RegistrationError('{model} has not been registered with django-reversion'.format(
            model = model,
        ))

    def unregister(self, model):
        """Removes a model from version control."""
        if not self.is_registered(model):
            raise RegistrationError('{model} has not been registered with django-reversion'.format(
                model = model,
            ))
        del self._registered_models[self._registration_key_for_model(model)]
        all_signals = self._signals[model] + self._eager_signals[model]
        for signal in all_signals:
            signal.disconnect(self._signal_receiver, model)
        del self._signals[model]
        del self._eager_signals[model]

        delattr(model, 'reversion_versions')
        model.reversion_versions = GenericRelation(Version)

    def _follow_relationships(self, objects):
        """Follows all relationships in the given set of objects."""
        followed = set()
        def _follow(obj, version_type, exclude_concrete):
            # Check the pk first because objects without a pk are not hashable
            if obj.pk is None or obj in followed or (obj.__class__, obj.pk) == exclude_concrete:
                return

            model_parent_list = obj._meta.get_parent_list()
            followed.add((obj, version_type))
            adapter = self.get_adapter(obj.__class__)
            for related in adapter.get_followed_relations(obj):
                _follow(related, version_type if related.__class__ in model_parent_list else Version.TYPE.FOLLOW,
                        exclude_concrete)
        for obj, version_type in objects:
            exclude_concrete = None
            if obj._meta.proxy:
                exclude_concrete = (obj._meta.concrete_model, obj.pk)
            _follow(obj, version_type, exclude_concrete)
        return followed

    def _get_versions(self, db=None):
        """Returns all versions that apply to this manager."""
        return Version.objects.using(db).filter(
            revision__manager_slug = self._manager_slug,
        ).select_related('revision')

    def save_revision(self, objects, user=None, comment='', meta=(), db=None):
        """Saves a new revision."""
        # Create the revision.
        if objects:
            # Follow relationships.
            for obj, follower_type in self._follow_relationships(
                    ((key, version_data.get('type')) for key, version_data in objects.items())
                ):
                if not obj in objects:
                    adapter = self.get_adapter(obj.__class__)
                    follow_obj_data = adapter.get_version_data(obj)
                    follow_obj_data['type'] = follower_type
                    objects[obj] = follow_obj_data

            # Create all the versions without saving them
            ordered_objects = list(objects.keys())
            new_versions = [Version(**objects[obj]) for obj in ordered_objects]
            # Check if there's some change in all the revision's objects.
            save_revision = True
            # Only save if we're always saving, or have changes.
            if save_revision:
                # Save a new revision.
                revision = Revision(
                    manager_slug = self._manager_slug,
                    user = user,
                    comment = comment,
                )
                # Send the pre_revision_commit signal.
                pre_revision_commit.send(self,
                    instances = ordered_objects,
                    revision = revision,
                    versions = new_versions,
                )
                # Save the revision.
                with transaction.atomic(using=db):
                    revision.save(using=db)
                    # Save version models.
                    for version in new_versions:
                        version.revision = revision
                        version.save()
                    # Save the meta information.
                    for cls, kwargs in meta:
                        cls._default_manager.db_manager(db).create(revision=revision, **kwargs)
                # Send the post_revision_commit signal.
                post_revision_commit.send(self,
                    instances = ordered_objects,
                    revision = revision,
                    versions = new_versions,
                )
                # Return the revision.
                return revision

    # Revision management API.

    def get_for_object_reference(self, model, object_id, db=None):
        """
        Returns all versions for the given object reference.

        The results are returned with the most recent versions first.
        """
        content_type = ContentType.objects.db_manager(db).get_for_model(model)
        versions = self._get_versions(db).filter(
            content_type = content_type,
        ).select_related('revision')
        if has_int_pk(model):
            # We can do this as a fast, indexed lookup.
            object_id_int = int(object_id)
            versions = versions.filter(object_id_int=object_id_int)
        else:
            # We can't do this using an index. Never mind.
            object_id = force_text(object_id)
            versions = versions.filter(object_id=object_id)
        versions = versions.order_by('-pk')
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
            'Use get_for_object().get_unique() instead of get_unique_for_object().',
            PendingDeprecationWarning)
        return list(self.get_for_object(obj, db).get_unique())

    def get_for_date(self, object, date, db=None):
        """Returns the latest version of an object for the given date."""
        versions = self.get_for_object(object, db)
        versions = versions.filter(revision__created_at__lte=date)
        try:
            version = versions[0]
        except IndexError:
            raise Version.DoesNotExist
        else:
            return version

    def get_deleted(self, model_class, db=None, model_db=None):
        """
        Returns all the deleted versions for the given model class.

        The results are returned with the most recent versions first.
        """
        model_db = model_db or db
        content_type = ContentType.objects.db_manager(db).get_for_model(model_class)
        live_pk_queryset = model_class._default_manager.db_manager(model_db).all().values_list('pk', flat=True)
        versioned_objs = self._get_versions(db).filter(
            content_type = content_type,
        )
        if has_int_pk(model_class):
            # If the model and version data are in different databases, decouple the queries.
            if model_db != db:
                live_pk_queryset = list(live_pk_queryset.iterator())
            # We can do this as a fast, in-database join.
            deleted_version_pks = versioned_objs.exclude(
                object_id_int__in = live_pk_queryset
            ).values_list('object_id_int')
        else:
            # This join has to be done as two separate queries.
            deleted_version_pks = versioned_objs.exclude(
                object_id__in = list(live_pk_queryset.iterator())
            ).values_list('object_id')
        deleted_version_pks = deleted_version_pks.annotate(
            latest_pk=Max('pk')
        ).values_list('latest_pk', flat=True)
        # HACK: MySQL deals extremely badly with this as a subquery, and can hang infinitely.
        # TODO: If a version is identified where this bug no longer applies, we can add a version specifier.
        if connection.vendor == 'mysql':  # pragma: no cover
            deleted_version_pks = list(deleted_version_pks)
        # Return the deleted versions!
        return self._get_versions(db).filter(pk__in=deleted_version_pks).order_by('-pk')

    # Signal receivers.
    def _signal_receiver(self, instance, signal, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            eager = signal in self._eager_signals[instance.__class__]
            adapter = self.get_adapter(instance.__class__)

            if signal in [pre_delete, post_delete]:
                type = Version.TYPE.DELETED
            elif signal == post_save:
                type = Version.TYPE.CREATED if kwargs.get('created') else Version.TYPE.CHANGED
            elif signal == pre_save:
                type = Version.TYPE.CREATED if instance.pk is None else Version.TYPE.CHANGED

            if eager:
                # pre_delete is a special case, because the instance will
                # be modified by django right after this.
                # don't use a lambda, but get the data out now.
                version_data = adapter.get_version_data(instance, self._revision_context_manager._db)
                self._revision_context_manager.add_to_context(self, type, copy.copy(instance), version_data)
                for obj, follower_type in self._follow_relationships([(instance, type)]):
                    adapter = self.get_adapter(obj.__class__)
                    version_data = adapter.get_version_data(obj, self._revision_context_manager._db)
                    self._revision_context_manager.add_to_context(self, follower_type, copy.copy(obj), version_data)
            else:
                version_data = lambda: adapter.get_version_data(instance, self._revision_context_manager._db)
                self._revision_context_manager.add_to_context(self, type, instance, version_data)


# A shared revision manager.
default_revision_manager = RevisionManager('default')


def create_command_revision(cls, manage_manually=False):
    """Login decorator for all methods inside test usage: @login(user_data)"""

    def _command_revision(cls):
        func = getattr(cls, 'handle')

        def _set_comment(*args, **kwargs):
            revision_context_manager.set_comment('Command log from "%s", args "%s"' % (sys.argv[1], ' '.join(sys.argv[2:])))
            return func(*args, **kwargs)

        setattr(cls, 'handle', revision_context_manager.create_revision(manage_manually)(_set_comment))
        return cls

    return _command_revision(cls)
