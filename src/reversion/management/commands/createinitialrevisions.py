from __future__ import unicode_literals

from optparse import make_option
try:
    from collections import OrderedDict
except ImportError:  # For Python 2.6
    from django.utils.datastructures import SortedDict as OrderedDict

try:
    from django.apps import apps
    try:
        get_app = apps.get_app
    except AttributeError:  # For Django >= 1.9
        get_app = lambda app_label: apps.get_app_config(app_label).models_module
    try:
        get_apps = apps.get_apps
    except AttributeError:  # For Django >= 1.9
        get_apps = lambda: [app_config.models_module for app_config in apps.get_app_configs() if app_config.models_module is not None]
    get_model = apps.get_model
    get_models = apps.get_models
except ImportError:  # For Django < 1.7
    from django.db.models import get_app, get_apps, get_model, get_models

try:
    from importlib import import_module
except ImportError:  # For Django < 1.8
    from django.utils.importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType
from django.db import reset_queries
from django.utils.encoding import force_text

from reversion.revisions import default_revision_manager
from reversion.models import Version, has_int_pk
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--comment",
            action="store",
            dest="comment",
            default="Initial version.",
            help='Specify the comment to add to the revisions. Defaults to "Initial version.".'),
        make_option("--batch-size",
            action="store",
            dest="batch_size",
            type=int,
            default=500,
            help="For large sets of data, revisions will be populated in batches. Defaults to 500"),
        make_option('--database', action='store', dest='database',
            help='Nominates a database to create revisions in.'),
        )
    args = '[appname, appname.ModelName, ...] [--comment="Initial version."]'
    help = "Creates initial revisions for a given app [and model]."

    def handle(self, *app_labels, **options):

        # Activate project's default language
        translation.activate(settings.LANGUAGE_CODE)

        comment = options["comment"]
        batch_size = options["batch_size"]
        database = options.get('database')

        verbosity = int(options.get("verbosity", 1))
        app_list = OrderedDict()
        # if no apps given, use all installed.
        if len(app_labels) == 0:
            for app in get_apps():
                if not app in app_list:
                    app_list[app] = []
                for model_class in get_models(app):
                    if not model_class in app_list[app]:
                        app_list[app].append(model_class)
        else:
            for label in app_labels:
                try:
                    app_label, model_label = label.split(".")
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)

                    model_class = get_model(app_label, model_label)
                    if model_class is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))
                    if app in app_list:
                        if app_list[app] and model_class not in app_list[app]:
                            app_list[app].append(model_class)
                    else:
                        app_list[app] = [model_class]
                except ValueError:
                    # This is just an app - no model qualifier.
                    app_label = label
                    try:
                        app = get_app(app_label)
                        if not app in app_list:
                            app_list[app] = []
                        for model_class in get_models(app):
                            if not model_class in app_list[app]:
                                app_list[app].append(model_class)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
        # Create revisions.
        for app, model_classes in app_list.items():
            for model_class in model_classes:
                self.create_initial_revisions(app, model_class, comment, batch_size, verbosity, database=database)

        # Go back to default language
        translation.deactivate()

    def create_initial_revisions(self, app, model_class, comment, batch_size, verbosity=2, database=None, **kwargs):
        """Creates the set of initial revisions for the given model."""
        # Import the relevant admin module.
        try:
            import_module("%s.admin" % app.__name__.rsplit(".", 1)[0])
        except ImportError:
            pass
        # Check all models for empty revisions.
        if default_revision_manager.is_registered(model_class):
            if verbosity >= 2:
                print("Creating initial revision(s) for model %s ..."  % (force_text(model_class._meta.verbose_name)))
            created_count = 0
            content_type = ContentType.objects.db_manager(database).get_for_model(model_class)
            versioned_pk_queryset = Version.objects.using(database).filter(content_type=content_type).all()
            live_objs = model_class._default_manager.using(database).all()
            if has_int_pk(model_class):
                # We can do this as a fast database join!
                live_objs = live_objs.exclude(
                    pk__in = versioned_pk_queryset.values_list("object_id_int", flat=True)
                )
            else:
                # This join has to be done as two separate queries.
                live_objs = live_objs.exclude(
                    pk__in = list(versioned_pk_queryset.values_list("object_id", flat=True).iterator())
                )
            # Save all the versions.
            ids = list(live_objs.values_list(model_class._meta.pk.name, flat=True))
            total = len(ids)
            for i in range(0, total, batch_size):
                chunked_ids = ids[i:i+batch_size]
                objects = live_objs.in_bulk(chunked_ids)
                for id, obj in objects.items():
                    try:
                        default_revision_manager.save_revision((obj,), comment=comment, db=database)
                    except:
                        print("ERROR: Could not save initial version for %s %s." % (model_class.__name__, obj.pk))
                        raise
                    created_count += 1
                reset_queries()
                if verbosity >= 2:
                    print("Created %s of %s." % (created_count, total))

            # Print out a message, if feeling verbose.
            if verbosity >= 2:
                print("Created %s initial revision(s) for model %s." % (created_count, force_text(model_class._meta.verbose_name)))
        else:
            if verbosity >= 2:
                print("Model %s is not registered."  % (force_text(model_class._meta.verbose_name)))
