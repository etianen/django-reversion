from __future__ import unicode_literals
from collections import namedtuple, defaultdict
from contextlib import contextmanager
from functools import wraps
from threading import local
from django.apps import apps
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, router
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.utils.encoding import force_text
from django.utils import timezone, six
from reversion.compat import remote_field
from reversion.errors import RevisionManagementError, RegistrationError
from reversion.signals import pre_revision_commit, post_revision_commit


_VersionOptions = namedtuple("VersionOptions", (
    "fields",
    "follow",
    "format",
    "for_concrete_model",
    "ignore_duplicates",
    "ignore_deletes",
))


_StackFrame = namedtuple("StackFrame", (
    "manage_manually",
    "user",
    "comment",
    "date_created",
    "db_versions",
    "meta",
))


class _Local(local):

    def __init__(self):
        self.stack = ()


_local = _Local()


def is_active():
    return bool(_local.stack)


def _current_frame():
    if not is_active():
        raise RevisionManagementError("There is no active revision for this thread")
    return _local.stack[-1]


def _copy_db_versions(db_versions):
    return {
        db: versions.copy()
        for db, versions
        in db_versions.items()
    }


def _push_frame(manage_manually, using):
    if is_active():
        current_frame = _current_frame()
        db_versions = _copy_db_versions(current_frame.db_versions)
        db_versions.setdefault(using, {})
        stack_frame = current_frame._replace(
            manage_manually=manage_manually,
            db_versions=db_versions,
        )
    else:
        stack_frame = _StackFrame(
            manage_manually=manage_manually,
            user=None,
            comment="",
            date_created=timezone.now(),
            db_versions={using: {}},
            meta=(),
        )
    _local.stack += (stack_frame,)


def _update_frame(**kwargs):
    _local.stack = _local.stack[:-1] + (_current_frame()._replace(**kwargs),)


def _pop_frame():
    prev_frame = _current_frame()
    _local.stack = _local.stack[:-1]
    if is_active():
        current_frame = _current_frame()
        db_versions = {
            db: prev_frame.db_versions[db]
            for db
            in current_frame.db_versions.keys()
        }
        _update_frame(
            user=prev_frame.user,
            comment=prev_frame.comment,
            date_created=prev_frame.date_created,
            db_versions=db_versions,
            meta=prev_frame.meta,
        )


def is_manage_manually():
    return _current_frame().manage_manually


def set_user(user):
    _update_frame(user=user)


def get_user():
    return _current_frame().user


def set_comment(comment):
    _update_frame(comment=comment)


def get_comment():
    return _current_frame().comment


def set_date_created(date_created):
    _update_frame(date_created=date_created)


def get_date_created():
    return _current_frame().date_created


def add_meta(model, **values):
    _update_frame(meta=_current_frame().meta + ((model, values),))


def _follow_relations(obj):
    version_options = _get_options(obj.__class__)
    for follow_name in version_options.follow:
        try:
            follow_obj = getattr(obj, follow_name)
        except ObjectDoesNotExist:
            continue
        if isinstance(follow_obj, models.Model):
            yield follow_obj
        elif isinstance(follow_obj, (models.Manager, QuerySet)):
            for follow_obj_instance in follow_obj.all():
                yield follow_obj_instance
        elif follow_obj is not None:
            raise RegistrationError("{name}.{follow_name} should be a Model or QuerySet".format(
                name=obj.__class__.__name__,
                follow_name=follow_name,
            ))


def _follow_relations_recursive(obj):
    def do_follow(obj):
        if obj not in relations:
            relations.add(obj)
            for related in _follow_relations(obj):
                do_follow(related)
    relations = set()
    do_follow(obj)
    return relations


def _add_to_revision(obj, using, model_db, explicit):
    from reversion.models import Version
    # Exit early if the object is not fully-formed.
    if obj.pk is None:
        return
    version_options = _get_options(obj.__class__)
    content_type = _get_content_type(obj.__class__, using)
    object_id = force_text(obj.pk)
    version_key = (content_type, object_id)
    # If the obj is already in the revision, stop now.
    db_versions = _current_frame().db_versions
    versions = db_versions[using]
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
    # Store the previous version if deletes are to be tracked, or if duplicates should be omitted
    version._previous = None
    if explicit and (not version_options.ignore_deletes or version_options.ignore_duplicates):
        version._previous = Version.objects.using(using).get_for_object(obj, model_db=model_db).first()
    # If the version is a duplicate, stop now.
    if version_options.ignore_duplicates and explicit and \
       version._previous and version._previous._local_field_dict == version._local_field_dict:
        return
    # Store the version.
    db_versions = _copy_db_versions(db_versions)
    db_versions[using][version_key] = version
    _update_frame(db_versions=db_versions)
    # Follow relations.
    for follow_obj in _follow_relations(obj):
        _add_to_revision(follow_obj, using, model_db, False)


def add_to_revision(obj, model_db=None):
    model_db = model_db or router.db_for_write(obj.__class__, instance=obj)
    for db in _current_frame().db_versions.keys():
        _add_to_revision(obj, db, model_db, True)


def _copy_version(version):
    return type(version)(
        content_type=version.content_type,
        object_id=version.object_id,
        db=version.db,
        format=version.format,
        serialized_data=version.serialized_data,
        object_repr=version.object_repr
    )


def _save_revision(versions, user=None, comment="", meta=(), date_created=None, using=None):
    from reversion.models import Revision
    # Directly save versions that exist in the database, and re-save the previous state for those that were deleted
    # Use _base_manager so we don't have problems when _default_manager is overriden
    model_db_pks = defaultdict(lambda: defaultdict(set))
    for version in versions:
        model_db_pks[version._model][version.db].add(version.object_id)
    model_db_existing_pks = {
        model: {
            db: frozenset(map(
                force_text,
                model._base_manager.using(db).filter(pk__in=pks).values_list("pk", flat=True),
            ))
            for db, pks in db_pks.items()
        }
        for model, db_pks in model_db_pks.items()
    }
    deleted = [
        _copy_version(version._previous)
        for version in versions
        if version._previous
        if version.object_id not in model_db_existing_pks[version._model][version.db]
    ]
    versions = [
        version for version in versions
        if version.object_id in model_db_existing_pks[version._model][version.db]
    ]
    versions.extend(deleted)
    # Bail early if there are no objects to save.
    if not versions:
        return
    # Save a new revision.
    revision = Revision(
        date_created=date_created,
        user=user,
        comment=comment,
    )
    # Send the pre_revision_commit signal.
    pre_revision_commit.send(
        sender=create_revision,
        revision=revision,
        versions=versions,
    )
    # Save the revision.
    revision.save(using=using)
    # Save version models.
    for version in versions:
        version.revision = revision
        version.save(using=using)
    # Save the meta information.
    for meta_model, meta_fields in meta:
        meta_model._base_manager.db_manager(using=using).create(
            revision=revision,
            **meta_fields
        )
    # Send the post_revision_commit signal.
    post_revision_commit.send(
        sender=create_revision,
        revision=revision,
        versions=versions,
    )


@contextmanager
def _dummy_context():
    yield


@contextmanager
def _create_revision_context(manage_manually, using, atomic):
    _push_frame(manage_manually, using)
    try:
        context = transaction.atomic(using=using) if atomic else _dummy_context()
        with context:
            yield
            # Only save for a db if that's the last stack frame for that db.
            if not any(using in frame.db_versions for frame in _local.stack[:-1]):
                current_frame = _current_frame()
                _save_revision(
                    versions=current_frame.db_versions[using].values(),
                    user=current_frame.user,
                    comment=current_frame.comment,
                    meta=current_frame.meta,
                    date_created=current_frame.date_created,
                    using=using,
                )
    finally:
        _pop_frame()


def create_revision(manage_manually=False, using=None, atomic=True):
    from reversion.models import Revision
    using = using or router.db_for_write(Revision)
    return _ContextWrapper(_create_revision_context, (manage_manually, using, atomic))


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


def _post_save_receiver(sender, instance, using, **kwargs):
    if is_registered(sender) and is_active() and not is_manage_manually():
        add_to_revision(instance, model_db=using)


def _pre_delete_receiver(sender, instance, using, **kwargs):
    # The same as _post_save_receiver, duplicated for clarity.
    if is_registered(sender) and is_active() and not is_manage_manually():
        add_to_revision(instance, model_db=using)


def _m2m_changed_receiver(instance, using, action, model, reverse, **kwargs):
    if action.startswith("post_") and not reverse:
        if is_registered(instance) and is_active() and not is_manage_manually():
            add_to_revision(instance, model_db=using)


def _get_registration_key(model):
    return (model._meta.app_label, model._meta.model_name)


_registered_models = {}


def is_registered(model):
    return _get_registration_key(model) in _registered_models


def get_registered_models():
    return (apps.get_model(*key) for key in _registered_models.keys())


def _get_senders_and_signals(model, options):
    yield model, post_save, _post_save_receiver
    if not options.ignore_deletes:
        yield model, pre_delete, _pre_delete_receiver
    opts = model._meta.concrete_model._meta
    for field in opts.local_many_to_many:
        m2m_model = remote_field(field).through
        if isinstance(m2m_model, six.string_types):
            if "." not in m2m_model:
                m2m_model = "{app_label}.{m2m_model}".format(
                    app_label=opts.app_label,
                    m2m_model=m2m_model
                )
        yield m2m_model, m2m_changed, _m2m_changed_receiver


def register(model=None, fields=None, exclude=(), follow=(), format="json",
             for_concrete_model=True, ignore_duplicates=False, ignore_deletes=True):
    def register(model):
        # Prevent multiple registration.
        if is_registered(model):
            raise RegistrationError("{model} has already been registered with django-reversion".format(
                model=model,
            ))
        # Parse fields.
        opts = model._meta.concrete_model._meta
        version_options = _VersionOptions(
            fields=tuple(
                field_name
                for field_name
                in ([
                    field.name
                    for field
                    in opts.local_fields + opts.local_many_to_many
                ] if fields is None else fields)
                if field_name not in exclude
            ),
            follow=tuple(follow),
            format=format,
            for_concrete_model=for_concrete_model,
            ignore_duplicates=ignore_duplicates,
            ignore_deletes=ignore_deletes,
        )
        # Register the model.
        _registered_models[_get_registration_key(model)] = version_options
        # Connect signals.
        for sender, signal, signal_receiver in _get_senders_and_signals(model, version_options):
            signal.connect(signal_receiver, sender=sender)
        # All done!
        return model
    # Return a class decorator if model is not given
    if model is None:
        return register
    # Register the model.
    return register(model)


def _assert_registered(model):
    if not is_registered(model):
        raise RegistrationError("{model} has not been registered with django-reversion".format(
            model=model,
        ))


def _get_options(model):
    _assert_registered(model)
    return _registered_models[_get_registration_key(model)]


def unregister(model):
    version_options = _get_options(model)
    del _registered_models[_get_registration_key(model)]
    # Disconnect signals.
    for sender, signal, signal_receiver in _get_senders_and_signals(model, version_options):
        signal.disconnect(signal_receiver, sender=sender)


def _get_content_type(model, using):
    from django.contrib.contenttypes.models import ContentType
    version_options = _get_options(model)
    return ContentType.objects.db_manager(using).get_for_model(
        model,
        for_concrete_model=version_options.for_concrete_model,
    )
