from __future__ import unicode_literals
from collections import defaultdict
from importlib import import_module
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import reset_queries, transaction
from django.utils import translation
from django.utils.encoding import force_text
from reversion.revisions import default_revision_manager
from reversion.models import Version


def get_app(app_label):
    return apps.get_app_config(app_label).models_module


class Command(BaseCommand):

    help = "Creates initial revisions for a given app [and model]."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label",
            nargs="*",
            help="Optional apps or app.Model list.",
        )
        parser.add_argument(
            "--comment",
            action="store",
            default="Initial version.",
            help="Specify the comment to add to the revisions. Defaults to 'Initial version'.")
        parser.add_argument(
            "--batch-size",
            action="store",
            type=int,
            default=500,
            help="For large sets of data, revisions will be populated in batches. Defaults to 500.",
        )
        parser.add_argument(
            "--database",
            help="Nominates a database to create revisions in.",
        )

    @transaction.atomic()
    def handle(self, *app_labels, **options):
        # Activate project's default language
        translation.activate(settings.LANGUAGE_CODE)
        # Parse options.
        comment = options["comment"]
        batch_size = options["batch_size"]
        database = options["database"]
        verbosity = int(options.get("verbosity", 1))
        # Look up apps.
        app_models = defaultdict(set)
        # If no apps given, use all installed.
        if len(app_labels) == 0:
            all_apps = [config.models_module for config in apps.get_app_configs()
                        if config.models_module is not None]
            for app in all_apps:
                for model_class in apps.get_models(app):
                    app_models[app].add(model_class)
        else:
            for label in app_labels:
                if "." in label:
                    # This is an app.Model specifier.
                    app_label, model_label = label.split(".")
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    model_class = apps.get_model(app_label, model_label)
                    if model_class is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))
                    app_models[app].add(model_class)
                else:
                    # This is just an app - no model qualifier.
                    app_label = label
                    try:
                        app = get_app(app_label)
                        for model_class in apps.get_models(app):
                            app_models[app].add(model_class)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
        # Create revisions.
        for app, model_classes in app_models.items():
            for model_class in model_classes:
                self.create_initial_revisions(app, model_class, comment, batch_size, verbosity, database=database)
        # Go back to default language
        translation.deactivate()

    def create_initial_revisions(self, app, model_class, comment, batch_size, verbosity=2, database=None, **kwargs):
        # Import the relevant admin module.
        try:
            import_module("%s.admin" % app.__name__.rsplit(".", 1)[0])
        except ImportError:
            pass
        # Check all models for empty revisions.
        if default_revision_manager.is_registered(model_class):
            if verbosity >= 2:
                self.stdout.write("Creating initial revision(s) for model %s ..." % (
                    force_text(model_class._meta.verbose_name)
                ))
            created_count = 0
            content_type = default_revision_manager._get_content_type(model_class, db=database)
            live_objs = model_class._base_manager.using(database).exclude(
                pk__reversion_in=(Version.objects.using(database).filter(
                    content_type=content_type,
                ), "object_id")
            )
            # Save all the versions.
            ids = list(live_objs.values_list("pk", flat=True).order_by())
            total = len(ids)
            for i in range(0, total, batch_size):
                chunked_ids = ids[i:i+batch_size]
                objects = live_objs.in_bulk(chunked_ids)
                for id, obj in objects.items():
                    try:
                        default_revision_manager.save_revision(
                            objects=(obj,),
                            comment=comment,
                            db=database,
                        )
                    except:
                        self.stdout.write("ERROR: Could not save initial version for %s %s." % (
                            model_class.__name__,
                            obj.pk,
                        ))
                        raise
                    created_count += 1
                reset_queries()
                if verbosity >= 2:
                    self.stdout.write("Created %s of %s." % (created_count, total))
            # Print out a message, if feeling verbose.
            if verbosity >= 2:
                self.stdout.write("Created %s initial revision(s) for model %s." % (
                    created_count,
                    force_text(model_class._meta.verbose_name),
                ))
        else:
            if verbosity >= 2:
                self.stdout.write("Model %s is not registered." % (force_text(model_class._meta.verbose_name)))
