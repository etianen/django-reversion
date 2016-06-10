from __future__ import unicode_literals
from collections import namedtuple
from contextlib import contextmanager
from functools import wraps
from threading import local
from weakref import WeakValueDictionary
from django.apps import apps
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, router
from django.db.models import Max
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils.encoding import force_text
from django.utils import timezone
from reversion.errors import RevisionManagementError, RegistrationError


_VersionOptions = namedtuple("VersionOptions", (
    "fields",
    "follow",
    "format",
    "for_concrete_model",
    "ignore_duplicates",
))


class _RevisionContextStackFrame(object):

    def __init__(self, manage_manually, db_set, user, comment, date_created, db_manager_versions, meta):
        self.manage_manually = manage_manually
        self.db_set = db_set
        self.user = user
        self.comment = comment
        self.date_created = date_created
        self.db_manager_versions = db_manager_versions
        self.meta = meta

    def fork(self, manage_manually, db):
        # Add the db to the current db set.
        db_set = self.db_set.copy()
        db_set.add(db)
        # Copy the manager versions.
        db_manager_versions = {
            db: {
                revision_manager: versions.copy()
                for revision_manager, versions
                in manager_versions.items()
            }
            for db, manager_versions
            in self.db_manager_versions.items()
        }
        db_manager_versions.setdefault(db, {})
        # Create the new stack frame.
        return _RevisionContextStackFrame(
            manage_manually,
            db_set,
            self.user,
            self.comment,
            self.date_created,
            db_manager_versions,
            self.meta[:],
        )

    def join(self, other_frame):
        self.user = other_frame.user
        self.comment = other_frame.comment
        self.date_created = other_frame.date_created
        self.db_manager_versions = {
            db: manager_versions.copy()
            for db, manager_versions
            in other_frame.db_manager_versions.items()
            if db in self.db_set
        }
        self.meta = other_frame.meta


class _RevisionContextManager(local):

    def __init__(self):
        self._stack = []


_revision_context_manager = _RevisionContextManager()


def is_active():
    return bool(_revision_context_manager._stack)


def _current_frame():
    if not is_active():
        raise RevisionManagementError("There is no active revision for this thread")
    return _revision_context_manager._stack[-1]


def is_manage_manually():
    return _current_frame().manage_manually


def set_user(user):
    _current_frame().user = user


def get_user():
    return _current_frame().user


def set_comment(comment):
    _current_frame().comment = comment


def get_comment():
    return _current_frame().comment


def get_date_created():
    return _current_frame().date_created


def set_date_created(date_created):
    _current_frame().date_created = date_created


def add_meta(model, **values):
    _current_frame().meta.append((model, values))


def _add_to_revision(revision_manager, obj, using, model_db, explicit):
    from reversion.models import Version
    model_db = _get_model_db(obj, obj.__class__, model_db)
    version_options = revision_manager._get_options(obj.__class__)
    versions = _current_frame().db_manager_versions[using].setdefault(revision_manager, {})
    content_type = revision_manager._get_content_type(obj.__class__, using)
    object_id = force_text(obj.pk)
    version_key = (content_type, object_id)
    # If the obj is already in the revision, stop now.
    if version_key in versions and not explicit:
        return
    # Get the version data.
    version = Version(
        content_type=content_type,
        object_id=object_id,
        db=model_db,
        format=version_options.format,
        serialized_data=serializers.serialize(
            version_options.format,
            (obj,),
            fields=version_options.fields,
        ),
        object_repr=force_text(obj),
    )
    # If the version is a duplicate, stop now.
    if version_options.ignore_duplicates and explicit:
        previous_version = revision_manager.get_for_object(obj, model_db=model_db, using=using).first()
        if previous_version and previous_version.local_field_dict == version.local_field_dict:
            return
    # Store the version.
    versions[version_key] = version
    # Follow relations.
    for follow_name in version_options.follow:
        try:
            follow_obj = getattr(obj, follow_name)
        except ObjectDoesNotExist:
            continue
        if isinstance(follow_obj, models.Model):
            _add_to_revision(revision_manager, follow_obj, using, model_db, False)
        elif isinstance(follow_obj, (models.Manager, QuerySet)):
            for follow_obj_instance in follow_obj.all():
                _add_to_revision(revision_manager, follow_obj_instance, using, model_db, False)
        elif follow_obj is not None:
            raise TypeError("{name}.{follow_name} should be a Model or QuerySet".format(
                name=obj.__class__.__name__,
                follow_name=follow_name,
            ))


def add_to_revision(obj, model_db=None):
    for db in _current_frame().db_set:
        for revision_manager in _revision_managers.values():
            if revision_manager.is_registered(obj.__class__):
                _add_to_revision(revision_manager, obj, db, model_db, True)


def _save_revision(revision_manager, versions, user=None, comment="", meta=(), date_created=None, using=None):
    from reversion.models import Revision
    # Bail early if there are no objects to save.
    if not versions:
        return
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
    revision.save(using=using)
    # Save version models.
    for version in versions:
        version.revision = revision
        version.save(using=using)
    # Save the meta information.
    for meta_instance in meta_instances:
        meta_instance.revision = revision
        meta_instance.save(using=using)


@contextmanager
def _create_revision_context(manage_manually, using):
    # Create a new stack frame.
    if is_active():
        stack_frame = _current_frame().fork(manage_manually, using)
    else:
        stack_frame = _RevisionContextStackFrame(
            manage_manually=manage_manually,
            db_set=set((using,)),
            user=None,
            comment="",
            date_created=timezone.now(),
            db_manager_versions={using: {}},
            meta=[],
        )
    # Run the revision context in a transaction.
    stack = _revision_context_manager._stack
    with transaction.atomic(using=using):
        stack.append(stack_frame)
        try:
            yield
        finally:
            stack.pop()
        # Only save for a db if that's the last stack frame for that db.
        if not any(using in frame.db_set for frame in _revision_context_manager._stack):
            for revision_manager, version_data in stack_frame.db_manager_versions[using].items():
                _save_revision(
                    revision_manager=revision_manager,
                    versions=version_data.values(),
                    user=stack_frame.user,
                    comment=stack_frame.comment,
                    meta=stack_frame.meta,
                    date_created=stack_frame.date_created,
                    using=using,
                )
        # Join the stack frame on success.
        if is_active():
            _current_frame().join(stack_frame)


def create_revision(manage_manually=False, using=None):
    from reversion.models import Revision
    using = router.db_for_write(Revision) if using is None else using
    return _ContextWrapper(_create_revision_context, (manage_manually, using))


class _ContextWrapper(object):

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


@receiver(post_save)
def _post_save_receiver(instance, using, **kwargs):
    if is_active() and not is_manage_manually():
        add_to_revision(instance, model_db=using)


@receiver(m2m_changed)
def _m2m_changed_receiver(instance, using, action, **kwargs):
    if action.startswith("post_") and is_active() and not is_manage_manually():
        add_to_revision(instance, model_db=using)


_revision_managers = WeakValueDictionary()


def _get_registration_key(model):
    return (model._meta.app_label, model._meta.model_name)


def _get_model_db(obj, model, model_db):
    return model_db or router.db_for_write(model, instance=obj)


class RevisionManager(object):

    def __init__(self, manager_slug):
        if manager_slug in _revision_managers:
            raise RegistrationError("A revision manager has already been created with the slug {slug}".format(
                slug=manager_slug,
            ))
        _revision_managers[manager_slug] = self
        self._manager_slug = manager_slug
        self._registered_models = {}

    # Registration methods.

    def is_registered(self, model):
        return _get_registration_key(model) in self._registered_models

    def get_registered_models(self):
        return (apps.get_model(*key) for key in self._registered_models.keys())

    def register(self, model=None, fields=None, exclude=(), follow=(), format="json",
                 for_concrete_model=True, ignore_duplicates=False):
        def register(model):
            # Prevent multiple registration.
            if self.is_registered(model):
                raise RegistrationError("{model} has already been registered with django-reversion".format(
                    model=model,
                ))
            # Parse fields.
            opts = model._meta
            version_options = _VersionOptions(
                fields=[
                    field_name
                    for field_name
                    in ([
                        field.name
                        for field
                        in opts.local_fields + opts.local_many_to_many
                    ] if fields is None else fields)
                    if field_name not in exclude
                ],
                follow=follow,
                format=format,
                for_concrete_model=for_concrete_model,
                ignore_duplicates=ignore_duplicates,
            )
            # Register the model.
            self._registered_models[_get_registration_key(model)] = version_options
            # All done!
            return model
        # Return a class decorator if model is not given
        if model is None:
            return register
        # Register the model.
        return register(model)

    def _assert_registered(self, model):
        if not self.is_registered(model):
            raise RegistrationError("{model} has not been registered with django-reversion".format(
                model=model,
            ))

    def _get_options(self, model):
        self._assert_registered(model)
        return self._registered_models[_get_registration_key(model)]

    def unregister(self, model):
        self._assert_registered(model)
        del self._registered_models[_get_registration_key(model)]

    # Helpers.

    def _get_content_type(self, model, using):
        from django.contrib.contenttypes.models import ContentType
        version_options = self._get_options(model)
        return ContentType.objects.db_manager(using).get_for_model(
            model,
            for_concrete_model=version_options.for_concrete_model,
        )

    # Lookup API.

    def get_for_model(self, model, using=None, model_db=None):
        from reversion.models import Revision, Version
        using = using or router.db_for_read(Revision)
        model_db = _get_model_db(None, model, model_db)
        content_type = self._get_content_type(model, using)
        return Version.objects.using(using).filter(
            revision__manager_slug=self._manager_slug,
            content_type=content_type,
            db=model_db,
        ).order_by("-pk")

    def get_for_object_reference(self, model, object_id, using=None, model_db=None):
        """
        Returns all versions for the given object reference.

        The results are returned with the most recent versions first.
        """
        return self.get_for_model(model, using=using, model_db=model_db).filter(
            object_id=object_id,
        )

    def get_for_object(self, obj, using=None, model_db=None):
        """
        Returns all the versions of the given object, ordered by date created.

        The results are returned with the most recent versions first.
        """
        return self.get_for_object_reference(obj.__class__, obj.pk, using=using, model_db=model_db)

    def get_deleted(self, model, using=None, model_db=None):
        """
        Returns all the deleted versions for the given model class.

        The results are returned with the most recent versions first.
        """
        return self.get_for_model(model, using=using, model_db=model_db).filter(
            pk__reversion_in=(self.get_for_model(model, using=using, model_db=model_db).exclude(
                object_id__reversion_in=(model._default_manager.using(model_db), model._meta.pk.name),
            ).values_list("object_id").annotate(
                id=Max("id"),
            ), "id")
        )


default_revision_manager = RevisionManager("default")

register = default_revision_manager.register
is_registered = default_revision_manager.is_registered
unregister = default_revision_manager.unregister
get_registered_models = default_revision_manager.get_registered_models
get_for_model = default_revision_manager.get_for_model
get_for_object_reference = default_revision_manager.get_for_object_reference
get_for_object = default_revision_manager.get_for_object
get_deleted = default_revision_manager.get_deleted
