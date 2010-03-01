"""Reversion management utilities."""


from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_syncdb
from django.utils.translation import ugettext as _
from django.utils.importlib import import_module

from reversion import models as reversion_app, revision
from reversion.models import Version 


def version_save(obj):
    """Saves the initial version of an object."""
    obj.save()
    revision.user = None
    revision.comment = _(u"Initial version.")
version_save = revision.create_on_success(version_save)


def create_initial_revisions(app, verbosity=2, **kwargs):
    """
    Post-syncdb hook to create an initial revision for all registered models.
    """
    # Import the relevant admin module.
    try:
        import_module("%s.admin" % app.__name__.rsplit(".", 1)[0])
    except ImportError:
        pass
    # Check all models for empty revisions.
    for model_class in models.get_models(app):
        if revision.is_registered(model_class):
            content_type = ContentType.objects.get_for_model(model_class)
            # Get the id for all models that have not got at least one revision.
            # HACK: This join can't be done in the database, for potential incompatibilities
            # between unicode object_ids and integer pks on strict backends like postgres.
            versioned_ids = frozenset(Version.objects.filter(content_type=content_type).values_list("object_id", flat=True).distinct().iterator())
            all_ids = frozenset(unicode(id) for id in model_class._default_manager.values_list("pk", flat=True).iterator())
            unversioned_ids = all_ids - versioned_ids
            # Create the initial revision for all unversioned models.
            created_count = 0
            for unversioned_obj in model_class._default_manager.filter(pk__in=unversioned_ids).iterator():
                version_save(unversioned_obj)
                created_count += 1
            # Print out a message, if feeling verbose.
            if created_count > 0 and verbosity >= 2:
                print u"Created %s initial revisions for model %s." % (created_count, model_class._meta.verbose_name)
            
        
post_syncdb.connect(create_initial_revisions)

