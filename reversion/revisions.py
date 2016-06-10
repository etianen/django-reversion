from __future__ import unicode_literals
from contextlib import contextmanager
from functools import wraps, partial
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


class VersionAdapter(object):

    """
    Adapter class for serializing a registered model.
    """

    def __init__(self, model):
        self.model = model

    signals = (post_save,)
    """
    Django signals that trigger saving a version.

    The model version will be saved at the end of the outermost revision block.
    """

    def get_signals(self):
        """
        Returns an iterable of all signals that trigger saving a version.
        """
        return self.signals

    fields = None
    """
    Field named to include in the serialized data.

    Set to `None` to include all model fields.
    """

    exclude = ()
    """
    Field names to exclude from the serialized data.
    """

    def get_fields(self, obj, db, model_db):
        """
        Returns an iterable of field names to serialize in the version data.
        """
        assert obj is not None
        assert db is not None
        assert model_db is not None
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

    format = "json"
    """
    The name of a Django serialization format to use when saving the version.
    """

    def get_format(self, obj, db, model_db):
        """
        Returns the name of a Django serialization format to use when saving the version.
        """
        assert obj is not None
        assert db is not None
        assert model_db is not None
        return self.format

    for_concrete_model = True
    """
    If `True` (default), then proxy models will be saved under the same content
    type as their concrete model. If `False`, then proxy models will be saved
    under their own content type, effectively giving proxy models their own
    distinct history.
    """

    def get_serialized_data(self, obj, db, model_db):
        """
        Returns a string of serialized data for the given model instance.
        """
        assert obj is not None
        assert db is not None
        assert model_db is not None
        return serializers.serialize(
            self.get_format(obj, db, model_db),
            (obj,),
            fields=list(self.get_fields(obj, db, model_db)),
        )

    def get_content_type(self, obj, db, model_db):
        """
        Returns the content type for the registered model.
        """
        from django.contrib.contenttypes.models import ContentType
        assert db is not None
        assert model_db is not None
        return ContentType.objects.db_manager(db).get_for_model(self.model, for_concrete_model=self.for_concrete_model)

    def get_object_repr(self, obj, db, model_db):
        """
        Returns a string representation of the model instance.
        """
        assert obj is not None
        assert db is not None
        assert model_db is not None
        return force_text(obj)

    def get_model_db(self, obj, db):
        """
        Returns the database where the model should be saved.
        """
        assert db is not None
        return router.db_for_write(self.model, instance=obj)

    def get_version(self, obj, db, model_db):
        """
        Returns a Version to be saved to the revision.
        """
        from reversion.models import Version
        assert obj is not None
        assert db is not None
        assert model_db is not None
        return Version(
            content_type=self.get_content_type(obj, db, model_db),
            object_id=force_text(obj.pk),
            db=model_db,
            format=self.get_format(obj, db, model_db),
            serialized_data=self.get_serialized_data(obj, db, model_db),
            object_repr=self.get_object_repr(obj, db, model_db),
        )

    follow = ()
    """
    Foreign-key relationships to follow when saving a version of this model.

    `ForeignKey`, `ManyToManyField` and reversion `ForeignKey` relationships
    are supported. Any property that returns a `Model` or `QuerySet`
    is also supported.
    """

    def get_follow(self, obj, db, model_db):
        """
        Returns an iterable of related models that should be included in the revision data.
        """
        for relationship in self.follow:
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

    def revert(self, version):
        """
        Reverts the given version to the database.
        """
        version.object_version.save(using=version.db)


class RevisionContextStackFrame(object):

    def __init__(self, manage_manually, db_set, user, comment, date_created, ignore_duplicates,
                 db_manager_objects, meta):
        # Block-scoped properties.
        self.manage_manually = manage_manually
        self.db_set = db_set
        # Revision-scoped properties.
        self.user = user
        self.comment = comment
        self.date_created = date_created
        self.ignore_duplicates = ignore_duplicates
        self.db_manager_objects = db_manager_objects
        self.meta = meta

    def fork(self, manage_manually, db):
        # Add the db to the current db set.
        db_set = self.db_set.copy()
        db_set.add(db)
        # Copy the manager db objects.
        db_manager_objects = {
            db: {
                revision_manager: objects.copy()
                for revision_manager, objects
                in manager_objects.items()
            }
            for db, manager_objects
            in self.db_manager_objects.items()
        }
        db_manager_objects.setdefault(db, {})
        # Create the new stack frame.
        return RevisionContextStackFrame(
            manage_manually,
            db_set,
            self.user,
            self.comment,
            self.date_created,
            self.ignore_duplicates,
            db_manager_objects,
            self.meta[:],
        )

    def join(self, other_frame):
        self.user = other_frame.user
        self.comment = other_frame.comment
        self.date_created = other_frame.date_created
        self.ignore_duplicates = other_frame.ignore_duplicates
        # Copy back the manager db objects, but only if they db is in this frame's db set.
        self.db_manager_objects = {
            db: manager_objects
            for db, manager_objects
            in other_frame.db_manager_objects.items()
            if db in self.db_set
        }
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

    def get_date_created(self):
        """Gets the date the revision was created."""
        return self._current_frame.date_created

    def set_date_created(self, date_created):
        """Sets the date the revision was created."""
        self._current_frame.date_created = date_created

    def set_ignore_duplicates(self, ignore_duplicates):
        """Sets whether to ignore duplicate revisions."""
        self._current_frame.ignore_duplicates = ignore_duplicates

    def get_ignore_duplicates(self):
        """Gets whether to ignore duplicate revisions."""
        return self._current_frame.ignore_duplicates

    def add_meta(self, model, **values):
        """Adds a model of meta information to the current revision."""
        self._current_frame.meta.append((model, values))

    def _add_to_context(self, revision_manager, obj, model_db, force):
        """
        Adds an object to the current revision.
        """
        adapter = revision_manager.get_adapter(obj.__class__)
        for db in self._current_frame.db_set:
            objects = self._current_frame.db_manager_objects[db].setdefault(revision_manager, {})
            model_db = adapter.get_model_db(obj, db) if model_db is None else model_db
            version = adapter.get_version(obj, db, model_db)
            version_key = (version.content_type, version.object_id)
            if version_key not in objects or force:
                objects[version_key] = (obj, version)
                # Follow relations.
                for relation in adapter.get_follow(obj, db, model_db):
                    self._add_to_context(revision_manager, obj, model_db, False)

    # Revision saving.

    def _save_revision(self, revision_manager, version_data, ignore_duplicates=False, user=None, comment="", meta=(),
                       date_created=None, db=None):
        from reversion.models import Revision
        # Bail early if there are no objects to save.
        instances, versions = zip(*version_data)
        # Check for duplicates, if requested.
        save_revision = True
        if ignore_duplicates:
            # Find the latest revision amongst the latest previous version of each object.
            latest_revision_qs = Revision.objects.using(db).annotate(
                version_count=models.Count("version"),
            ).filter(
                version_count=len(versions),
                manager_slug=revision_manager._manager_slug,
            )
            for version in versions:
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
                save_revision = get_version_keys(previous_versions) != get_version_keys(versions)
        # Only save if we're always saving, or have changes.
        if save_revision:
            # Save a new revision.
            revision = Revision(
                manager_slug=revision_manager._manager_slug,
                date_created=date_created,
                user=user,
                comment=comment,
            )
            # Create the meta objects.
            meta_instances = [
                meta_model(**meta_fields)
                for meta_model, meta_fields
                in meta
            ]
            # Save the revision.
            revision.save(using=db)
            # Save version models.
            for version in versions:
                version.revision = revision
                version.save(using=db)
            # Save the meta information.
            for meta_instance in meta_instances:
                meta_instance.revision = revision
                meta_instance.save(using=db)
            # Return the revision.
            return revision

    # Context management.

    @contextmanager
    def _create_revision_context(self, manage_manually, db):
        # Create a new stack frame.
        if self.is_active():
            stack_frame = self._current_frame.fork(manage_manually, db)
        else:
            stack_frame = RevisionContextStackFrame(
                manage_manually=manage_manually,
                db_set=set((db,)),
                user=None,
                comment="",
                date_created=timezone.now(),
                ignore_duplicates=False,
                db_manager_objects={db: {}},
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
            if not any(db in frame.db_set for frame in self._stack):
                for revision_manager, version_data in stack_frame.db_manager_objects[db].items():
                    self._save_revision(
                        revision_manager=revision_manager,
                        version_data=version_data.values(),
                        user=stack_frame.user,
                        comment=stack_frame.comment,
                        meta=stack_frame.meta,
                        date_created=stack_frame.date_created,
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
        return iter(cls._created_managers.values())

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
        for signal in adapter_obj.get_signals():
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
        for signal in adapter_obj.get_signals():
            signal.disconnect(self._signal_receiver, model)

    # Revision management API.

    def get_for_model(self, model, db=None, model_db=None):
        from reversion.models import Revision, Version
        adapter = self.get_adapter(model)
        db = router.db_for_read(Revision) if db is None else db
        model_db = adapter.get_model_db(None, db) if model_db is None else model_db
        content_type = adapter.get_content_type(None, db, model_db)
        return Version.objects.using(db).filter(
            revision__manager_slug=self._manager_slug,
            content_type=content_type,
            db=model_db,
        )

    def get_for_object_reference(self, model, object_id, db=None, model_db=None):
        """
        Returns all versions for the given object reference.

        The results are returned with the most recent versions first.
        """
        return self.get_for_model(model, db=db, model_db=model_db).filter(
            object_id=object_id,
        ).order_by("-pk")

    def get_for_object(self, obj, db=None, model_db=None):
        """
        Returns all the versions of the given object, ordered by date created.

        The results are returned with the most recent versions first.
        """
        return self.get_for_object_reference(obj.__class__, obj.pk, db=db, model_db=model_db)

    def get_deleted(self, model, db=None, model_db=None):
        """
        Returns all the deleted versions for the given model class.

        The results are returned with the most recent versions first.
        """
        return self.get_for_model(model, db=db, model_db=model_db).filter(
            pk__reversion_in=(self.get_for_model(model, db=db, model_db=model_db).exclude(
                object_id__reversion_in=(model._default_manager.using(model_db), model._meta.pk.name),
            ).values_list("object_id").annotate(
                id=Max("id"),
            ), "id")
        ).order_by("-id")

    # Manual revision saving.

    def add_to_revision(self, obj, model_db=None):
        self._revision_context_manager._add_to_context(self, obj, model_db, True)

    # Signal receivers.

    def _signal_receiver(self, instance, using, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            self.add_to_revision(instance, model_db=using)


# A shared revision manager.
default_revision_manager = RevisionManager("default")


# Easy registration methods.
register = default_revision_manager.register
is_registered = default_revision_manager.is_registered
unregister = default_revision_manager.unregister
get_adapter = default_revision_manager.get_adapter
get_registered_models = default_revision_manager.get_registered_models


# Manual revision saving.
add_to_revision = default_revision_manager.add_to_revision


# Context management.
create_revision = revision_context_manager.create_revision


# Revision meta data.
get_user = revision_context_manager.get_user
set_user = revision_context_manager.set_user
get_comment = revision_context_manager.get_comment
set_comment = revision_context_manager.set_comment
get_date_created = revision_context_manager.get_date_created
set_date_created = revision_context_manager.set_date_created
add_meta = revision_context_manager.add_meta
get_ignore_duplicates = revision_context_manager.get_ignore_duplicates
set_ignore_duplicates = revision_context_manager.set_ignore_duplicates


# Low level API.
get_for_model = default_revision_manager.get_for_model
get_for_object_reference = default_revision_manager.get_for_object_reference
get_for_object = default_revision_manager.get_for_object
get_deleted = default_revision_manager.get_deleted
