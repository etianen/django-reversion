"""Revision management for django-reversion."""


try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

import operator, sys
from threading import local
from weakref import WeakValueDictionary

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.signals import request_finished
from django.db import models, DEFAULT_DB_ALIAS, connection
from django.db.models import Q, Max
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_delete

from reversion.models import Revision, Version, VERSION_ADD, VERSION_CHANGE, VERSION_DELETE, has_int_pk, deprecated, pre_revision_commit, post_revision_commit


class VersionAdapter(object):
    
    """Adapter class for serializing a registered model."""
    
    # Fields to include in the serialized data.
    fields = ()
    
    # Fields to exclude from the serialized data.
    exclude = ()
    
    # Foreign key relationships to follow when saving a version of this model.
    follow = ()
    
    # The serialization format to use.
    format = "json"
    
    def __init__(self, model):
        """Initializes the version adapter."""
        self.model = model
        
    def get_fields_to_serialize(self):
        """Returns an iterable of field names to serialize in the version data."""
        opts = self.model._meta
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
            except ObjectDoesNotExist:
                continue
            if isinstance(related, models.Model):
                yield related
            elif isinstance(related, (models.Manager, QuerySet)):
                for related_obj in related.all():
                    yield related_obj
            elif related is not None:
                raise TypeError, "Cannot follow the relationship %r. Expected a model or QuerySet, found %r" % (relationship, related)
    
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
        
    def get_version_data(self, obj, type_flag, db=None):
        """Creates the version data to be saved to the version model."""
        object_id = unicode(obj.pk)
        db = db or DEFAULT_DB_ALIAS
        content_type = ContentType.objects.db_manager(db).get_for_model(obj)
        if has_int_pk(obj.__class__):
            object_id_int = int(obj.pk)
        else:
            object_id_int = None
        return {
            "object_id": object_id,
            "object_id_int": object_id_int,
            "content_type": content_type,
            "format": self.get_serialization_format(),
            "serialized_data": self.get_serialized_data(obj),
            "object_repr": unicode(obj),
            "type": type_flag
        }


class RevisionManagementError(Exception):
    
    """Exception that is thrown when something goes wrong with revision managment."""

          
class RevisionContextManager(local):
    
    """Manages the state of the current revision."""
    
    def __init__(self):
        """Initializes the revision state."""
        self.clear()
        # Connect to the request finished signal.
        request_finished.connect(self._request_finished_receiver)
    
    def clear(self):
        """Puts the revision manager back into its default state."""
        self._objects = {}
        self._user = None
        self._comment = ""
        self._stack = []
        self._is_invalid = False
        self._meta = []
        self._ignore_duplicates = False
        self._db = None
    
    def is_active(self):
        """Returns whether there is an active revision for this thread."""
        return bool(self._stack)
    
    def is_managing_manually(self):
        """Returns whether this revision context has manual management enabled."""
        self._assert_active()
        return self._stack[-1]
    
    def _assert_active(self):
        """Checks for an active revision, throwning an exception if none."""
        if not self.is_active():
            raise RevisionManagementError("There is no active revision for this thread")
        
    def start(self, manage_manually=False):
        """
        Begins a revision for this thread.
        
        This MUST be balanced by a call to `end`.  It is recommended that you
        leave these methods alone and instead use the revision context manager
        or the `create_on_success` decorator.
        """
        self._stack.append(manage_manually)
    
    def end(self):
        """Ends a revision for this thread."""
        self._assert_active()
        self._stack.pop()
        if not self._stack:
            try:
                if not self.is_invalid():
                    # Save the revision data.
                    for manager, manager_context in self._objects.iteritems():
                        manager.save_revision(
                            dict(
                                (obj, callable(data) and data() or data)
                                for obj, data
                                in manager_context.iteritems()
                            ),
                            user = self._user,
                            comment = self._comment,
                            meta = self._meta,
                            ignore_duplicates = self._ignore_duplicates,
                            db = self._db,
                        )
            finally:
                self.clear()

    def invalidate(self):
        """Marks this revision as broken, so should not be commited."""
        self._assert_active()
        self._is_invalid = True
        
    def is_invalid(self):
        """Checks whether this revision is invalid."""
        return self._is_invalid
    
    def add_to_context(self, manager, obj, version_data):
        """Adds an object to the current revision."""
        self._assert_active()
        try:
            manager_context = self._objects[manager]
        except KeyError:
            manager_context = {}
            self._objects[manager] = manager_context
        manager_context[obj] = version_data

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
        
    def add_meta(self, cls, **kwargs):
        """Adds a class of meta information to the current revision."""
        self._assert_active()
        self._meta.append((cls, kwargs))
    
    def set_ignore_duplicates(self, ignore_duplicates):
        """Sets whether to ignore duplicate revisions."""
        self._assert_active()
        self._ignore_duplicates = ignore_duplicates
        
    def get_ignore_duplicates(self):
        """Gets whether to ignore duplicate revisions."""
        self._assert_active()
        return self._ignore_duplicates
    
    # Signal receivers.
    
    def _request_finished_receiver(self, **kwargs):
        """
        Called at the end of a request, ensuring that any open revisions
        are closed. Not closing all active revisions can cause memory leaks
        and weird behaviour.
        """
        while self.is_active():
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
            self.__enter__()
            exception = False
            try:
                try:
                    return func(*args, **kwargs)
                except:
                    exception = True
                    if not self.__exit__(*sys.exc_info()):
                        raise
            finally:
                if not exception:
                    self.__exit__(None, None, None)
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
        # Proxies to common context methods.
        self._revision_context = revision_context_manager.create_revision()
        self.create_on_success = deprecated("@revision.create_on_success", "@reversion.create_revision")(self._revision_context)
        self.add_meta = deprecated("revision.add_meta()", "reversion.add_meta()")(revision_context_manager.add_meta)

    # Registration methods.

    def is_registered(self, model):
        """
        Checks whether the given model has been registered with this revision
        manager.
        """
        return model in self._registered_models
    
    def get_registered_models(self):
        """Returns an iterable of all registered models."""
        return self._registered_models.keys()
        
    def register(self, model, adapter_cls=VersionAdapter, **field_overrides):
        """Registers a model with this revision manager."""
        # Prevent multiple registration.
        if self.is_registered(model):
            raise RegistrationError, "%r has already been registered with django-reversion" % model
        # Prevent proxy models being registered.
        if model._meta.proxy:
            raise RegistrationError("Proxy models cannot be used with django-reversion, register the parent class instead")
        # Perform any customization.
        if field_overrides:
            adapter_cls = type("Custom" + adapter_cls.__name__, (adapter_cls,), field_overrides)
        # Perform the registration.
        adapter_obj = adapter_cls(model)
        self._registered_models[model] = adapter_obj
        # Connect to the post save signal of the model.
        post_save.connect(self._post_save_receiver, model)
        pre_delete.connect(self._pre_delete_receiver, model)
    
    def get_adapter(self, model):
        """Returns the registration information for the given model class."""
        if self.is_registered(model):
            return self._registered_models[model]
        raise RegistrationError, "%r has not been registered with django-reversion" % model
        
    def unregister(self, model):
        """Removes a model from version control."""
        if not self.is_registered(model):
            raise RegistrationError, "%r has not been registered with django-reversion" % model
        del self._registered_models[model]
        post_save.disconnect(self._post_save_receiver, model)
        pre_delete.disconnect(self._pre_delete_receiver, model)
    
    def _follow_relationships(self, objects):
        """Follows all relationships in the given set of objects."""
        followed = set()
        def _follow(obj):
            if obj in followed or obj.pk is None:
                return
            followed.add(obj)
            adapter = self.get_adapter(obj.__class__)
            for related in adapter.get_followed_relations(obj):
                _follow(related)
        for obj in objects:
            _follow(obj)
        return followed
    
    def _get_versions(self, db=None):
        """Returns all versions that apply to this manager."""
        db = db or DEFAULT_DB_ALIAS
        return Version.objects.using(db).filter(
            revision__manager_slug = self._manager_slug,
        ).select_related("revision")
        
    def save_revision(self, objects, ignore_duplicates=False, user=None, comment="", meta=(), db=None):
        """Saves a new revision."""
        # Get the db alias.
        db = db or DEFAULT_DB_ALIAS
        # Adapt the objects to a dict.
        if isinstance(objects, (list, tuple)):
            objects = dict(
                (obj, self.get_adapter(obj.__class__).get_version_data(obj, VERSION_CHANGE, db))
                for obj in objects
            )
        # Create the revision.
        if objects:
            # Follow relationships.
            for obj in self._follow_relationships(objects.iterkeys()):
                if not obj in objects:
                    adapter = self.get_adapter(obj.__class__)
                    objects[obj] = adapter.get_version_data(obj, VERSION_CHANGE)
            # Create all the versions without saving them
            ordered_objects = list(objects.iterkeys())
            new_versions = [Version(**objects[obj]) for obj in ordered_objects]
            # Check if there's some change in all the revision's objects.
            save_revision = True
            if ignore_duplicates:
                # Find the latest revision amongst the latest previous version of each object.
                subqueries = [Q(object_id=version.object_id, content_type=version.content_type) for version in new_versions]
                subqueries = reduce(operator.or_, subqueries)
                latest_revision = self._get_versions(db).filter(subqueries).aggregate(Max("revision"))["revision__max"]
                # If we have a latest revision, compare it to the current revision.
                if latest_revision is not None:
                    previous_versions = self._get_versions(db).filter(revision=latest_revision).values_list("serialized_data", flat=True)
                    if len(previous_versions) == len(new_versions):
                        all_serialized_data = [version.serialized_data for version in new_versions]
                        if sorted(previous_versions) == sorted(all_serialized_data):
                            save_revision = False
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
                revision.save(using=db)
                # Save version models.
                for version in new_versions:
                    version.revision = revision
                    version.save(using=db)
                # Save the meta information.
                for cls, kwargs in meta:
                    cls._default_manager.db_manager(db).create(revision=revision, **kwargs)
                # Send the pre_revision_commit signal.
                post_revision_commit.send(self,
                    instances = ordered_objects,
                    revision = revision,
                    versions = new_versions,
                )
                # Return the revision.
                return revision
                
    
    # Context management.
    
    @deprecated("reversion.revision", "reversion.create_revision()")
    def __enter__(self, *args, **kwargs):
        """Enters a revision management block."""
        return self._revision_context.__enter__(*args, **kwargs)
        
    @deprecated("reversion.revision", "reversion.create_revision()")
    def __exit__(self, *args, **kwargs):
        """Leaves a block of revision management."""
        return self._revision_context.__exit__(*args, **kwargs)
    
    # Revision meta data.
    
    user = property(
        deprecated("revision.user", "reversion.get_user()")(lambda self: self._revision_context_manager.get_user()),
        deprecated("revision.user", "reversion.set_user()")(lambda self, user: self._revision_context_manager.set_user(user)),
    )
    
    comment = property(
        deprecated("revision.comment", "reversion.get_comment()")(lambda self: self._revision_context_manager.get_comment()),
        deprecated("revision.comment", "reversion.set_comment()")(lambda self, comment: self._revision_context_manager.set_comment(comment)),
    )
    
    ignore_duplicates = property(
        deprecated("revision.ignore_duplicates", "reversion.get_ignore_duplicates()")(lambda self: self._revision_context_manager.get_ignore_duplicates()),
        deprecated("revision.ignore_duplicates", "reversion.set_ignore_duplicates()")(lambda self, ignore_duplicates: self._revision_context_manager.set_ignore_duplicates(ignore_duplicates))
    )
    
    # Revision management API.
    
    def get_for_object_reference(self, model, object_id, db=None):
        """
        Returns all versions for the given object reference.
        
        The results are returned with the most recent versions first.
        """
        db = db or DEFAULT_DB_ALIAS
        content_type = ContentType.objects.db_manager(db).get_for_model(model)
        versions = self._get_versions(db).filter(
            content_type = content_type,
        ).select_related("revision")
        if has_int_pk(model):
            # We can do this as a fast, indexed lookup.
            object_id_int = int(object_id)
            versions = versions.filter(object_id_int=object_id_int)
        else:
            # We can't do this using an index. Never mind.
            object_id = unicode(object_id)
            versions = versions.filter(object_id=object_id)
        versions = versions.order_by("-pk")
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
        versions = self.get_for_object(obj, db)
        changed_versions = []
        last_serialized_data = None
        for version in versions:
            if last_serialized_data != version.serialized_data:
                changed_versions.append(version)
            last_serialized_data = version.serialized_data
        return changed_versions
    
    def get_for_date(self, object, date, db=None):
        """Returns the latest version of an object for the given date."""
        versions = self.get_for_object(object, db)
        versions = versions.filter(revision__date_created__lte=date)
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
        db = db or DEFAULT_DB_ALIAS
        model_db = model_db or db
        content_type = ContentType.objects.db_manager(db).get_for_model(model_class)
        live_pk_queryset = model_class._default_manager.db_manager(model_db).all().values_list("pk", flat=True)
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
            ).values_list("object_id_int")
        else:
            # This join has to be done as two separate queries.
            deleted_version_pks = versioned_objs.exclude(
                object_id__in = list(live_pk_queryset.iterator())
            ).values_list("object_id")
        deleted_version_pks = deleted_version_pks.exclude(
            type = VERSION_DELETE,
        ).annotate(
            latest_pk = Max("pk")
        ).values_list("latest_pk", flat=True)
        # HACK: MySQL deals extremely badly with this as a subquery, and can hang infinitely.
        # TODO: If a version is identified where this bug no longer applies, we can add a version specifier.
        if connection.vendor == "mysql":
            deleted_version_pks = list(deleted_version_pks)
        # Return the deleted versions!
        return self._get_versions(db).filter(pk__in=deleted_version_pks).order_by("-pk")
        
    # Signal receivers.
        
    def _post_save_receiver(self, instance, created, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            adapter = self.get_adapter(instance.__class__)
            if created:
                version_data = lambda: adapter.get_version_data(instance, VERSION_ADD, self._revision_context_manager._db)
            else:
                version_data = lambda: adapter.get_version_data(instance, VERSION_CHANGE, self._revision_context_manager._db)
            self._revision_context_manager.add_to_context(self, instance, version_data)
            
    def _pre_delete_receiver(self, instance, **kwargs):
        """Adds registered models to the current revision, if any."""
        if self._revision_context_manager.is_active() and not self._revision_context_manager.is_managing_manually():
            adapter = self.get_adapter(instance.__class__)
            version_data = adapter.get_version_data(instance, VERSION_DELETE, self._revision_context_manager._db)
            self._revision_context_manager.add_to_context(self, instance, version_data)

        
# A shared revision manager.
default_revision_manager = RevisionManager("default")
