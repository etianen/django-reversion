from contextvars import ContextVar
from collections import namedtuple, defaultdict
from contextlib import contextmanager
from functools import wraps
from django.apps import apps
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, router
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, m2m_changed
from django.utils.encoding import force_str
from django.utils import timezone
from reversion.errors import RevisionManagementError, RegistrationError
from reversion.signals import pre_revision_commit, post_revision_commit


_VersionOptions = namedtuple("VersionOptions", (
    "fields",
    "follow",
    "format",
    "for_concrete_model",
    "ignore_duplicates",
    "use_natural_foreign_keys",
))


_StackFrame = namedtuple("StackFrame", (
    "manage_manually",
    "user",
    "comment",
    "date_created",
    "db_versions",
    "meta",
    # @override
    "saves",
))


_stack = ContextVar("reversion-stack", default=[])


def is_active():
    return bool(_stack.get())


def _current_frame():
    if not is_active():
        raise RevisionManagementError("There is no active revision for this thread")
    return _stack.get()[-1]


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
            # @override
            saves=defaultdict(set),
        )
    _stack.set(_stack.get() + [stack_frame])


def _update_frame(**kwargs):
    _stack.get()[-1] = _current_frame()._replace(**kwargs)


def _pop_frame():
    prev_frame = _current_frame()
    stack = _stack.get()
    del stack[-1]
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
    object_id = force_str(obj.pk)
    version_key = (content_type, object_id)

    # @override Refresh from db when there are multiple instances
    # saving in the same transaction to prevent saving inconsistent
    # data due to .save(update_fields=[])
    frame = _current_frame()
    frame.saves[version_key].add(id(obj))

    if len(frame.saves[version_key]) > 1:
        obj.refresh_from_db()

    # If the obj is already in the revision, stop now.
    db_versions = frame.db_versions
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
            use_natural_foreign_keys=version_options.use_natural_foreign_keys,
        ),
        object_repr=force_str(obj),
    )
    # If the version is a duplicate, stop now.
    if version_options.ignore_duplicates and explicit:
        previous_version = Version.objects.using(using).get_for_object(obj, model_db=model_db).first()
        if previous_version and previous_version._local_field_dict == version._local_field_dict:
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


def _save_revision(versions, user=None, comment="", meta=(), date_created=None, using=None):
    from reversion.models import Revision

    # @override Deleted code that prevents saving deleted events.

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
    context = transaction.atomic(using=using) if atomic else _dummy_context()
    with context:
        _push_frame(manage_manually, using)
        try:
            yield
            # Only save for a db if that's the last stack frame for that db.
            if not any(using in frame.db_versions for frame in _stack.get()[:-1]):
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


def _get_senders_and_signals(model):
    yield model, post_save, _post_save_receiver
    opts = model._meta.concrete_model._meta
    for field in opts.local_many_to_many:
        m2m_model = field.remote_field.through
        if isinstance(m2m_model, str):
            if "." not in m2m_model:
                m2m_model = "{app_label}.{m2m_model}".format(
                    app_label=opts.app_label,
                    m2m_model=m2m_model
                )
        yield m2m_model, m2m_changed, _m2m_changed_receiver


def register(model=None, fields=None, exclude=(), follow=(), format="json",
             for_concrete_model=True, ignore_duplicates=False, use_natural_foreign_keys=False):
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
            use_natural_foreign_keys=use_natural_foreign_keys,
        )
        # Register the model.
        _registered_models[_get_registration_key(model)] = version_options
        # Connect signals.
        for sender, signal, signal_receiver in _get_senders_and_signals(model):
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
    _assert_registered(model)
    del _registered_models[_get_registration_key(model)]
    # Disconnect signals.
    for sender, signal, signal_receiver in _get_senders_and_signals(model):
        signal.disconnect(signal_receiver, sender=sender)


def _get_content_type(model, using):
    from django.contrib.contenttypes.models import ContentType
    version_options = _get_options(model)
    return ContentType.objects.db_manager(using).get_for_model(
        model,
        for_concrete_model=version_options.for_concrete_model,
    )
